# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp_account.tests.test_valuation_layers import TestMrpValuationCommon
from odoo.tests import Form

from datetime import datetime, timedelta


class TestMrpWorkorderHrValuation(TestMrpValuationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'group_ids': [(4, grp_workorder.id)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Jean Michel',
            'hourly_cost': 100,
        })

        cls.employee_center = cls.env['mrp.workcenter'].create({
            'name': 'Jean Michel\'s Center',
            'costs_hour': 10,
            'employee_ids': [(4, cls.employee.id)],
        })

        cls.bom.operation_ids = [(0, 0, {
            'name': 'Super Operation',
            'workcenter_id': cls.employee_center.id,
            'time_mode': 'manual',
            'time_cycle_manual': 60,
        })]

    def test_workcenter_employee_cost_impacting_on_valuation(self):
        """
            When the employee's *cost per hour* is set on the employee's form, it
            must override the workcenter's *employee cost per hour* for AVCO/FIFO
            products. However, if the employee's cost per hour is zero, then the
            workcenter's employee cost per hour should be used on valuations.
        """
        def produce():
            mo_form = Form(self.env['mrp.production'])
            mo_form.bom_id = self.bom
            mo = mo_form.save()
            mo.action_confirm()

            with Form(mo) as mo_form:
                mo_form.qty_producing = 1

            # Register a productivity of one hour
            now = datetime.now()
            workorder = mo.workorder_ids
            productivity = self.env['mrp.workcenter.productivity'].create({
                'employee_id': self.employee.id,
                'workcenter_id': self.employee_center.id,
                'workorder_id': workorder.id,
                'date_start': now,
                'date_end': now + timedelta(hours=1),
                'loss_id': self.env.ref('mrp.block_reason7').id,
            })
            workorder.button_finish()
            mo.button_mark_done()

            return mo, productivity

        def assert_employee_cost(expected_employee_cost):
            self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.remaining_value, 10 + expected_employee_cost, f'Workcenter cost (10) + Employee cost ({expected_employee_cost})')
            self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.unit_cost, 10 + expected_employee_cost, f'Workcenter cost (10) + Employee cost ({expected_employee_cost})')
            # Test that mrp_cost_structure report is correctly calculated with employee cost
            self.env.flush_all()  # Need to flush for mrp report
            report_cost = self.env['report.mrp_account_enterprise.mrp_cost_structure']._get_report_values(docids=mo.id)['lines'][0]
            self.assertEqual(report_cost['total_cost_operations'], 10 + expected_employee_cost)
            report_overview = self.env['report.mrp.report_mo_overview'].get_report_values(mo.id)
            self.assertEqual(report_overview['data']['operations']['details'][1]['unit_cost'], expected_employee_cost)

        self.employee_center.employee_costs_hour = 50

        # 1) cost_method: fifo
        self.product1.categ_id.property_cost_method = 'fifo'

        # 1.1) hourly_cost set on employee's form
        self.employee.hourly_cost = 100
        mo, _ = produce()
        assert_employee_cost(100)

        # 1.2) hourly_cost not set on employee's form
        self.employee.hourly_cost = 0
        mo, _ = produce()
        assert_employee_cost(50) # must use workcenter's costs_hour

        # 2) cost_method: avco
        self.product1.categ_id.property_cost_method = 'average'

        # 2.1) hourly_cost set on employee's form
        self.employee.hourly_cost = 100
        mo, _ = produce()
        assert_employee_cost(100)

        # 2.2) hourly_cost not set on employee's form
        self.employee.hourly_cost = 0
        mo, _ = produce()
        assert_employee_cost(50) # must use workcenter's costs_hour

        # 3) changing employee cost after done the MO
        self.product1.categ_id.property_cost_method = 'average'
        self.employee.hourly_cost = 100
        mo, productivity = produce()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(productivity.employee_cost, 100)
        self.assertEqual(productivity.total_cost, 100)
        self.employee.hourly_cost = 50
        self.assertEqual(productivity.employee_cost, 100, 'The productivity employee cost must remain unchanged after done the MO')
        self.assertEqual(productivity.total_cost, 100, 'Productivity time cost must remain unchanged after done the MO')

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayrollCommon(TransactionCase):

    def setUp(self):
        super().setUp()

        Bank = self.env['res.partner.bank']
        Employee = self.env['hr.employee']
        in_country = self.env.ref('base.in')
        rd_dept = self.env['hr.department'].create({
            'name': 'Research and Development',
        })
        employee_fp = self.env.ref('hr.employee_admin')

        self.company_in = self.env['res.company'].create({
            'name': 'Company IN',
            'country_id': self.env.ref('base.in').id,
        })

        self.env = self.env(context=dict(self.env.context, allowed_company_ids=self.company_in.ids))

        in_bank = self.env['res.bank'].create({
            'name': 'Bank IN',
            'bic': 'ABCD0123456'
        })

        self.rahul_emp = Employee.create({
            'name': 'Rahul',
            'country_id': in_country.id,
            'department_id': rd_dept.id,
            'company_id': self.company_in.id,
            'l10n_in_esic_number': 93874944361284657,
        })

        self.jethalal_emp = Employee.create({
            'name': 'Jethalal',
            'country_id': in_country.id,
            'department_id': rd_dept.id,
            'company_id': self.company_in.id,
            'l10n_in_esic_number': 93487475100284657,
        })

        res_bank = Bank.create({
            'acc_number': '3025632343043',
            'partner_id': self.rahul_emp.work_contact_id.id,
            'acc_type': 'bank',
            'bank_id': in_bank.id,
            'allow_out_payment': True,
        })
        self.rahul_emp.bank_account_id = res_bank

        res_bank_1 = Bank.create({
            'acc_number': '3025632343044',
            'partner_id': self.jethalal_emp.work_contact_id.id,
            'acc_type': 'bank',
            'bank_id': in_bank.id,
            'allow_out_payment': True,
        })
        self.jethalal_emp.bank_account_id = res_bank_1

        self.contract_rahul = self.env['hr.contract'].create({
            'date_start': date(2023, 1, 1),
            'date_end':  date(2023, 1, 31),
            'name': 'Rahul Probation contract',
            'wage': 5000.0,
            'l10n_in_esic_amount': 20.0,
            'employee_id': self.rahul_emp.id,
            'state': 'open',
            'hr_responsible_id': employee_fp.id,
        })

        self.contract_jethalal = self.env['hr.contract'].create({
            'date_start': date(2023, 1, 1),
            'date_end':  date(2023, 1, 31),
            'name': 'Jethalal Probation contract',
            'wage': 5000.0,
            'employee_id': self.jethalal_emp.id,
            'state': 'open',
            'l10n_in_esic_amount': 20.0,
            'hr_responsible_id': employee_fp.id,
        })

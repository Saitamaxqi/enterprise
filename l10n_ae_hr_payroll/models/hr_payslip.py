# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from itertools import chain

from odoo import api, models, Command


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _l10n_ae_get_wps_formatted_amount(self, val):
        currency = self.env.ref('base.AED')
        return f'{currency.round(val):.{currency.decimal_places}f}'

    def _l10n_ae_get_wps_data(self):
        rows = []
        input_codes = [
            "HOUALLOWINP",
            "CONVALLOWINP",
            "MEDALLOWINP",
            "ANNUALPASSALLOWINP",
            "OVERTIMEALLOWINP",
            "OTALLOWINP",
            "LEAVEENCASHINP",
        ]
        inputs_dict = self._get_line_values(input_codes)

        for payslip in self:
            employee = payslip.employee_id
            unpaid_leave_days = payslip.worked_days_line_ids.filtered(
                lambda x: x.work_entry_type_id in payslip.struct_id.unpaid_work_entry_type_ids)
            unpaid_leave_day_count = sum(unpaid_leave_days.mapped('number_of_days'))
            evp_inputs = [inputs_dict[code][payslip.id]['total'] for code in input_codes]
            total_evp = sum(evp_inputs)

            rows.append([
                "EDR",
                (employee.identification_id or '').zfill(14),
                employee.bank_account_id.bank_id.l10n_ae_routing_code or '',
                employee.bank_account_id.acc_number or '',
                payslip.date_from.strftime('%Y-%m-%d'),
                payslip.date_to.strftime('%Y-%m-%d'),
                (payslip.date_to - payslip.date_from).days + 1,
                self._l10n_ae_get_wps_formatted_amount(payslip.net_wage - total_evp),
                self._l10n_ae_get_wps_formatted_amount(total_evp),
                unpaid_leave_day_count
            ])

            if not payslip.currency_id.is_zero(total_evp):
                rows.append([
                    "EVP",
                    (employee.identification_id or '').zfill(14),
                    employee.bank_account_id.bank_id.l10n_ae_routing_code or '',
                    *map(self._l10n_ae_get_wps_formatted_amount, evp_inputs)
                ])

        return rows

    @api.depends('employee_id', 'version_id', 'struct_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        super()._compute_input_line_ids()
        balance_by_employee = self._get_salary_advance_balances_by_employee()
        uae_employee_struct = self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure')

        for slip in self:
            if not slip.employee_id or slip.country_code != "AE":
                continue
            if slip.struct_id == uae_employee_struct:
                balance = balance_by_employee[slip.employee_id]
                if balance <= 0:
                    continue
                sal_adv_rec_type = self.env.ref('l10n_ae_hr_payroll.l10n_ae_input_advance_recovery')
                new_input_lines = [
                    Command.unlink(line.id)
                    for line in slip.input_line_ids.filtered_domain([('input_type_id', '=', sal_adv_rec_type.id)])
                ]
                new_input_lines.append(Command.create({
                    'name': self.env._('Salary Advance Recovery'),
                    'amount': balance,
                    'input_type_id': sal_adv_rec_type.id,
                }))
                slip.write({'input_line_ids': new_input_lines})

    def _get_salary_advance_balances_by_employee(self):
        payslips_by_employee = self._read_group(
            domain=[
                ('state', 'in', ('done', 'paid')),
                ('employee_id', 'in', self.employee_id.ids),
                ('input_line_ids.code', 'in', ('ADV', 'ADVREC')),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset']
        )
        balance_by_employee = defaultdict(float)
        for employee_id, payslips in payslips_by_employee:
            for input_line in chain.from_iterable(payslip.input_line_ids for payslip in payslips):
                if input_line.code == 'ADV':
                    balance_by_employee[employee_id] += input_line.amount
                elif input_line.code == 'ADVREC':
                    balance_by_employee[employee_id] -= input_line.amount
        return balance_by_employee

    def action_payslip_payment_report(self, export_format='l10n_ae_wps'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.payment.report.wizard',
            'view_mode': 'form',
            'view_id': 'hr_payslip_payment_report_view_form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_payslip_ids': self.ids,
                'default_payslip_run_id': self.payslip_run_id.id,
                'default_export_format': export_format,
            },
        }

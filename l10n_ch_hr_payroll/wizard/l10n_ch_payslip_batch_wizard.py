# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _


class ChHrPayslipEmployees(models.TransientModel):
    _name = 'l10n.ch.hr.payslip.montlhy.wizard'
    _description = 'Generate Monthly Pay'

    name = fields.Char()
    year = fields.Integer(string="Year", required=True, default=lambda self: fields.Date.today().year)
    month = fields.Selection(string="Month", selection=[
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], required=True, default=lambda self: str((fields.Date.today()).month))

    employee_ids = fields.Many2many('hr.employee')
    department_id = fields.Many2many('hr.department')
    contract_type = fields.Many2many('hr.contract.type', domain=lambda self: [('id', 'in', self.env['hr.version']._get_allowed_contract_type_ids())])
    workplace_id = fields.Many2many('l10n.ch.location.unit')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company.id)
    pay_13th = fields.Boolean(string="Pay 13th Month")

    def action_create(self):
        # 1) Compute from/to dates for selected year & month
        from_date = date(self.year, int(self.month), 1)
        to_date = from_date + relativedelta(months=1, days=-1)

        # 2) Create a payslip batch
        if self.name:
            batch_name = self.name
        else:
            batch_name = _("Monthly Batch %(year)s-%(month)s", year=self.year, month=str(self.month).zfill(2))
        payslip_run = self.env['hr.payslip.run'].create({
            'name': batch_name,
            'company_id': self.company_id.id,
            'date_start': from_date,
            'date_end': to_date,
            'l10n_ch_pay_13th_month': self.pay_13th
        })

        all_contracts = self.env['l10n.ch.occupation'].search([])

        # todo : fix this sudo
        valid_contracts = all_contracts.sudo().filtered(lambda c: c.date_start and c.employee_id.company_id == self.company_id and c.date_start <= to_date and (not c.date_end or c.date_end >= from_date))

        Payslip = self.env['hr.payslip']
        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []

        for contract in valid_contracts:
            values = {
                **default_values,
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'company_id': self.company_id.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'version_id': contract.employee_id._get_version(max(contract.date_start, from_date)).id,
                'struct_id': self.env.ref("l10n_ch_hr_payroll.hr_payroll_structure_ch_elm").id,
            }
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        payslips.compute_sheet()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip Run'),
            'res_model': 'hr.payslip.run',
            'view_mode': 'form',
            'res_id': payslip_run.id,
        }

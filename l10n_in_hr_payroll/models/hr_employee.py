# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from datetime import timedelta
from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_in_uan = fields.Char(string='UAN', groups="hr.group_hr_user", copy=False)
    l10n_in_pan = fields.Char(string='PAN', groups="hr.group_hr_user", copy=False)
    l10n_in_esic_number = fields.Char(string='ESIC Number', groups="hr.group_hr_user", copy=False)
    l10n_in_relationship = fields.Char("Relationship", groups="hr.group_hr_user", tracking=True)
    l10n_in_lwf_account_number = fields.Char("LWF Account Number", groups="hr.group_hr_user", tracking=True)
    l10n_in_tds = fields.Float(readonly=False, related="version_id.l10n_in_tds", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_driver_salay = fields.Boolean(readonly=False, related="version_id.l10n_in_driver_salay", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_medical_insurance = fields.Float(readonly=False, related="version_id.l10n_in_medical_insurance", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_provident_fund = fields.Boolean(readonly=False, related="version_id.l10n_in_provident_fund", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_voluntary_provident_fund = fields.Float(readonly=False, related="version_id.l10n_in_voluntary_provident_fund", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_house_rent_allowance_metro_nonmetro = fields.Float(readonly=False, related="version_id.l10n_in_house_rent_allowance_metro_nonmetro", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_supplementary_allowance = fields.Float(readonly=False, related="version_id.l10n_in_supplementary_allowance", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_gratuity = fields.Float(readonly=False, related="version_id.l10n_in_gratuity", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_esic_amount = fields.Float(readonly=False, related="version_id.l10n_in_esic_amount", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_leave_allowance = fields.Float(readonly=False, related="version_id.l10n_in_leave_allowance", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_in_residing_child_hostel = fields.Integer(readonly=False, related="version_id.l10n_in_residing_child_hostel", inherited=True, groups="hr_payroll.group_hr_payroll_user")

    _unique_l10n_in_uan = models.Constraint(
        'unique (l10n_in_uan)',
        "This UAN already exists",
    )
    _unique_l10n_in_pan = models.Constraint(
        'unique (l10n_in_pan)',
        "This PAN already exists",
    )
    _unique_l10n_in_esic_number = models.Constraint(
        'unique (l10n_in_esic_number)',
        "This ESIC Number already exists",
    )

    def _get_employees_with_invalid_ifsc(self):
        return self.filtered(lambda emp: not bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", emp.bank_account_id.bank_bic or '')))

    @api.model
    def notify_expiring_contract_work_permit(self):
        contract_type_id = self.env.ref('l10n_in_hr_payroll.l10n_in_contract_type_probation', raise_if_not_found=False)
        if contract_type_id:
            one_week_ago = fields.Date.today() - timedelta(weeks=1)
            versions = self.env['hr.version'].search([
                ('contract_date_end', '=', one_week_ago), ('contract_type_id', '=', contract_type_id.id)
            ])
            for version in versions:
                version.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=version.hr_responsible_id.id,
                    note=_("End date of %(name)s's contract is today.", name=version.employee_id.name),
                )
        return super().notify_expiring_contract_work_permit()

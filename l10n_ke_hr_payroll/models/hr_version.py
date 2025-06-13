# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_ke_pension_contribution = fields.Monetary("Pension Contribution", groups="hr.group_hr_user")
    l10n_ke_food_allowance = fields.Monetary("Food Allowance", groups="hr.group_hr_user")
    l10n_ke_airtime_allowance = fields.Monetary("Airtime Allowance", groups="hr.group_hr_user")
    l10n_ke_pension_allowance = fields.Monetary("Pension Allowance", groups="hr.group_hr_user")
    l10n_ke_voluntary_medical_insurance = fields.Monetary("Voluntary medical Insurance", groups="hr.group_hr_user")
    l10n_ke_life_insurance = fields.Monetary("Life Insurance", groups="hr.group_hr_user")
    l10n_ke_is_li_managed_by_employee = fields.Boolean(
        string="Managed by Employee", groups="hr.group_hr_user",
        help="If selected, Life Insurance will be paid by the employee on his own, only the life insurance relief will be deduced from payslip.")
    l10n_ke_education = fields.Monetary("Education", groups="hr.group_hr_user")
    l10n_ke_is_secondary = fields.Boolean(
        string="Secondary Contract", groups="hr.group_hr_user",
        help="Check if the employee got a main contract in another company.")
    l10n_ke_mortgage = fields.Monetary(string="Mortgage Interest", currency_field='currency_id', groups="hr.group_hr_user")

    @api.constrains('l10n_ke_mortgage')
    def _check_l10n_ke_mortgage(self):
        max_amount_yearly = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('l10n_ke_max_mortgage', raise_if_not_found=False)
        for version in self:
            if max_amount_yearly and version.l10n_ke_mortgage > max_amount_yearly:
                raise UserError(_('The mortgage interest cannot exceed %s Ksh yearly.', max_amount_yearly))

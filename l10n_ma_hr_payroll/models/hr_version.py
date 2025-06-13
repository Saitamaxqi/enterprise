from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_ma_kilometric_exemption = fields.Monetary(
        string='Kilometric Exemption', groups="hr.group_hr_user",
        tracking=True)
    l10n_ma_transport_exemption = fields.Monetary(
        string='Transportation Exemption', groups="hr.group_hr_user",
        tracking=True)
    l10n_ma_hra = fields.Monetary(string='HRA', tracking=True, help="House rent allowance.", groups="hr.group_hr_user")
    l10n_ma_da = fields.Monetary(string="DA", help="Dearness allowance", groups="hr.group_hr_user")
    l10n_ma_meal_allowance = fields.Monetary(string="Meal Allowance", help="Meal allowance", groups="hr.group_hr_user")
    l10n_ma_medical_allowance = fields.Monetary(string="Medical Allowance", help="Medical allowance", groups="hr.group_hr_user")

from odoo import models, fields


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_sa_housing_allowance = fields.Monetary(string='Saudi Housing Allowance', groups="hr.group_hr_user")
    l10n_sa_transportation_allowance = fields.Monetary(string='Saudi Transportation Allowance', groups="hr.group_hr_user")
    l10n_sa_other_allowances = fields.Monetary(string='Saudi Other Allowances', groups="hr.group_hr_user")
    l10n_sa_number_of_days = fields.Float(string='Saudi Number of Days', groups="hr.group_hr_user", default=21,
        help='Number of days of basic salary to be added to the end of service provision per year')
    l10n_sa_wps_description = fields.Char(string="WPS Payment Description", groups="hr.group_hr_user")
    l10n_sa_iqama_annual_amount = fields.Monetary(string="Iqama Annual Amount", groups="hr.group_hr_user")
    l10n_sa_medical_insurance_annual_amount = fields.Monetary(string="Medical Insurance Annual Amount", groups="hr.group_hr_user")
    l10n_sa_work_permit_annual_amount = fields.Monetary(string="Work Permit Annual Amount", groups="hr.group_hr_user")

    _l10n_sa_hr_payroll_number_of_days_constraint = models.Constraint(
        'CHECK(l10n_sa_number_of_days >= 0)',
        "Number of Days must be equal to or greater than 0",
    )

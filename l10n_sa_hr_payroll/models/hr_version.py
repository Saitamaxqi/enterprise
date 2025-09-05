from odoo import models, fields


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_sa_housing_allowance = fields.Monetary(string='Saudi Housing Allowance', groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_transportation_allowance = fields.Monetary(string='Saudi Transportation Allowance', groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_other_allowances = fields.Monetary(string='Saudi Other Allowances', groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_number_of_days = fields.Integer(string='Saudi Number of Days', default=21, groups="hr_payroll.group_hr_payroll_user",
                                            help='Number of days of basic salary to be added to the end of service provision per year')
    l10n_sa_wps_description = fields.Char(string="WPS Payment Description", groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_iqama_annual_amount = fields.Monetary(string="Iqama Annual Amount", groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_medical_insurance_annual_amount = fields.Monetary(string="Medical Insurance Annual Amount", groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_work_permit_annual_amount = fields.Monetary(string="Work Permit Annual Amount", groups="hr_payroll.group_hr_payroll_user")

    _l10n_sa_hr_payroll_number_of_days_constraint = models.Constraint(
        'CHECK(l10n_sa_number_of_days >= 0)',
        "Number of Days must be equal to or greater than 0",
    )

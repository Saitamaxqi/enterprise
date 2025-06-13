# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrVersion(models.Model):
    _inherit = "hr.version"

    l10n_ae_housing_allowance = fields.Monetary(string="Housing Allowance", groups="hr.group_hr_user")
    l10n_ae_transportation_allowance = fields.Monetary(string="Transportation Allowance", groups="hr.group_hr_user")
    l10n_ae_other_allowances = fields.Monetary(string="Other Allowances", groups="hr.group_hr_user")
    l10n_ae_is_dews_applied = fields.Boolean(string="Is DEWS Applied", groups="hr.group_hr_user",
                                             help="Daman Investments End of Service Programme")
    l10n_ae_number_of_leave_days = fields.Integer(string="Number of Leave Days", default=30, groups="hr.group_hr_user",
                                                  help="Number of leave days of gross salary to be added to the annual leave provision per month")
    l10n_ae_is_computed_based_on_daily_salary = fields.Boolean(string="Computed Based On Daily Salary", groups="hr.group_hr_user",
                                                               help="If True, The EOS will be computed based on the daily salary provided rather than the basic salary")
    l10n_ae_eos_daily_salary = fields.Float(string="Daily Salary", groups="hr.group_hr_user")

    _l10n_ae_hr_payroll_number_of_leave_days_constraint = models.Constraint(
        'CHECK(l10n_ae_number_of_leave_days >= 0)',
        "Number of Leave Days must be equal to or greater than 0",
    )

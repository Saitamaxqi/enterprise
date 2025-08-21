from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_sk_meal_voucher_employee = fields.Monetary("Meal Vouchers Amount (Employee)", groups="hr_payroll.group_hr_payroll_user")
    l10n_sk_meal_voucher_employer = fields.Monetary("Meal Vouchers Amount (Employer)", groups="hr_payroll.group_hr_payroll_user")

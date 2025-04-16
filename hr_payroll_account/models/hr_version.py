from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'
    _description = 'Employee Contract'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account', check_company=True, groups="hr.group_hr_user")

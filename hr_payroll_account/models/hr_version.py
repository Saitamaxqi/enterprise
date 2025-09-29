from odoo import fields, models


class HrVersion(models.Model):
    _name = 'hr.version'
    _inherit = ['hr.version', "analytic.mixin"]
    _description = 'Employee Contract'

    analytic_distribution = fields.Json(groups="hr.group_hr_user", tracking=True)
    analytic_precision = fields.Integer(groups="hr.group_hr_user", tracking=True)
    distribution_analytic_account_ids = fields.Many2many(groups="hr.group_hr_user", tracking=True)

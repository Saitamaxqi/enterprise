from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_ro_work_type = fields.Selection([
        ('1', 'Normal Conditions'),
        ('2', 'Particular Conditions'),
        ('3', 'Special Conditions')
    ], string='Work type', default="1", groups="hr_payroll.group_hr_payroll_user")

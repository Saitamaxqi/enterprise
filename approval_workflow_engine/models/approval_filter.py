from odoo import models, fields


class ApprovalFilter(models.Model):
    _name = 'approval.filter'
    _description = 'Approval Filter'

    name = fields.Char(string='Filter Name', required=True)

    group_id = fields.Many2one(
        'approval.group',
        string='Approval Group',
        required=True,
        ondelete='cascade'
    )

    field_name = fields.Char(
        string='Field Name',
        required=True,
        help='Technical field name on the target document, such as amount_total'
    )

    operator = fields.Selection([
        ('=', '='),
        ('!=', '!='),
        ('>', '>'),
        ('<', '<'),
        ('>=', '>='),
        ('<=', '<='),
    ], string='Operator', required=True, default='=')

    value = fields.Char(
        string='Value',
        required=True,
        help='Value to compare against'
    )

    active = fields.Boolean(default=True)
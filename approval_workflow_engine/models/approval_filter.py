from odoo import models, fields, api


class ApprovalFilter(models.Model):
    _name = 'approval.filter'
    _description = 'Approval Filter'

    name = fields.Char(string='Filter Name')

    group_id = fields.Many2one(
        'approval.group',
        string='Approval Group',
        required=True,
        ondelete='cascade'
    )

    stage_id = fields.Many2one(
        'approval.stage',
        string='Approval Stage',
        related='group_id.stage_id',
        store=True,
        readonly=True
    )

    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        related='stage_id.workflow_id',
        store=True,
        readonly=True
    )

    model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        related='workflow_id.model_id',
        store=True,
        readonly=True
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Document Field',
        required=True,
        domain="[('model_id', '=', model_id)]",
        ondelete='cascade'
    )

    field_name = fields.Char(
        string='Field Technical Name',
        related='field_id.name',
        store=True,
        readonly=True
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
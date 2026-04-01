from odoo import models, fields


class ApprovalStage(models.Model):
    _name = 'approval.stage'
    _description = 'Approval Stage'
    _order = 'workflow_id, sequence, id'

    name = fields.Char(string='Stage Name', required=True)

    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='Sequence',
        required=True,
        default=10
    )

    group_ids = fields.One2many(
        'approval.group',
        'stage_id',
        string='Approval Groups'
    )
    comment_required = fields.Boolean(string='Comment Required', default=True)
    active = fields.Boolean(default=True)
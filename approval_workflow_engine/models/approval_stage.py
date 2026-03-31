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
        default=10,
        required=True
    )

    approver_type = fields.Selection(
        [('user', 'User'), ('group', 'Group'),('record_based', 'Record Based')],
        string='Approver Type',
        required=True,
        default='user'
    )

    user_ids = fields.Many2many(
        'res.users',
        'approval_stage_user_rel',
        'stage_id',
        'user_id',
        string='Approver Users'
    )

    group_ids = fields.Many2many(
        'res.groups',
        'approval_stage_group_rel',
        'stage_id',
        'group_id',
        string='Approver Groups'
    )
    can_approve = fields.Boolean(_compute='_compute_can_approve', string='Can Approve') # to be done later

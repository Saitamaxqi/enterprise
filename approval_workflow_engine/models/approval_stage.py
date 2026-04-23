from odoo import models, fields, api


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
    #should add sequence for this field to be able to order the stages in the workflow
    sequence = fields.Integer(
        string='Sequence',
        readonly=True,
        default=1
    )

    filter_ids = fields.One2many(
        'approval.filter',
        'stage_id',
        string='Filters'
    )

    group_ids = fields.One2many(
        'approval.group',
        'stage_id',
        string='Approval Groups'
    )
    comment_required = fields.Boolean(string='Comment Required', default=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence', 1) == 1:
                vals['sequence'] = self.env['ir.sequence'].next_by_code('approval.stage') or 1
        return super().create(vals_list)
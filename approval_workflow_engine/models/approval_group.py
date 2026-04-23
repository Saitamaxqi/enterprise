from odoo import models, fields, api


class ApprovalGroup(models.Model):
    _name = 'approval.group'
    _description = 'Approval Group'
    
    group_id = fields.Many2one(
        'res.groups',
        string='Selected Group',
        required=True
    )
    name = fields.Char(compute='_compute_name', string='Group Name', store=True)

    stage_id = fields.Many2one(
        'approval.stage',
        string='Approval Stage',
        required=True,
        ondelete='cascade'
    )



    filter_ids = fields.One2many(
        'approval.filter',
        'group_id',
        string='Filters'
    )

    active = fields.Boolean(default=True)

    @api.depends('group_id.name')
    def _compute_name(self):
        for record in self:
            record.name = record.group_id.name if record.group_id else ''
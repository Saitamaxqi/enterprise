from odoo import models, fields, api

class ApprovalWorkflow(models.Model):
    _name = 'approval.workflow'
    _description = 'Approval Workflow'

    name = fields.Char(string='Name', required=True)
    model_id = fields.One2many(
        'ir.model',
        'workflow_id',
    )

    model_name = fields.Char(
        string='Model Technical Name',
        related='model_id.model',
        store=True,
        readonly=True
    )
    stages_ids = fields.One2many('approval.stage', 'workflow_id', string='Stages')
    stage_count = fields.Integer(compute="_")
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('stage_ids')
    def _compute_stage_count(self):
        for record in self:
            record.stage_count = len(record.stage_ids)
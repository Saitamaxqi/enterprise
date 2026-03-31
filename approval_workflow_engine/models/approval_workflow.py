from odoo import models, fields

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
    number_of_stages = fields.Integer(string='Number of Stages', required=True, default=1)
    stages_ids = fields.One2many('approval.stage', 'workflow_id', string='Stages')
    active = fields.Boolean(string='Active', default=True)
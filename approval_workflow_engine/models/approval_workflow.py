from odoo import models, fields

class ApprovalWorkflow(models.Model):
    _name = 'approval.workflow'
    _description = 'Approval Workflow'

    name = fields.Char(string='Name', required=True)
    number_of_stages = fields.Integer(string='Number of Stages', required=True, default=1)
    stages_ids = fields.One2many('approval.stage', 'workflow_id', string='Stages')
    active = fields.Boolean(string='Active', default=True)
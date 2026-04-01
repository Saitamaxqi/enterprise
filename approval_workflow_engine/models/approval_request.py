from odoo import models, fields

class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New')
    res_model = fields.Char(string='Resource Model', required=True, readonly=True)
    res_id = fields.Integer(string='Resource ID', required=True, readonly=True)
    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        required=True,
        tracking=True,
        ondelete = 'cascade'
    )
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )
    current_stage_id = fields.Many2one(
        'approval.stage',
        string='Current Stage',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting','Waiting'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], string='Status', default='draft', tracking=True)
       
    log_ids = fields.One2many(
        'approval.log',
        'request_id',
        string='Approval Logs'
    )
    #bussnis logic and action buttons later
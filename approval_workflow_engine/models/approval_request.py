from odoo import models, fields, api, _
from odoo.exceptions import UserError

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
    #bussnis logic
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))

            first_stage = self.env['approval.stage'].search(
                [('workflow_id', '=', record.workflow_id.id)],
                order='sequence asc',
                limit=1
            )
            #this may be handeled in a different way later
            if not first_stage:
                raise UserError(_('This workflow has no stages configured.'))

            record.stage_id = first_stage
            record.state = 'waiting'

            record.message_post(body=_('Approval request submitted.'))

    def action_approve(self):
        for record in self:
            if record.state not in ['waiting', 'in_progress']:
                raise UserError(_('Only requests waiting for approval can be approved.'))

            if not record.can_current_user_approve:
                raise UserError(_('You are not allowed to approve this request.'))
            #this will be handled differently for the comment part
            self.env['approval.log'].create({
                'request_id': record.id,
                'user_id': self.env.user.id,
                'action': 'approved',
                'comment': 'Approved',
            })

            next_stage = self.env['approval.stage'].search([
                ('workflow_id', '=', record.workflow_id.id),
                ('sequence', '>', record.stage_id.sequence)
            ], order='sequence asc', limit=1)

            if next_stage:
                record.stage_id = next_stage
                record.state = 'in_progress'
                record.message_post(body=_('Approval moved to next stage: %s') % next_stage.name)
            else:
                record.state = 'approved'
                record.message_post(body=_('Approval request fully approved.'))

    def action_reject(self):
        for record in self:
            if record.state not in ['waiting', 'in_progress']:
                raise UserError(_('Only requests waiting for approval can be rejected.'))

            if not record.can_current_user_approve:
                raise UserError(_('You are not allowed to reject this request.'))
            #this will be handled differently for the comment part
            self.env['approval.log'].create({
                'request_id': record.id,
                'user_id': self.env.user.id,
                'action': 'rejected',
                'comment': 'Rejected',
            })

            record.state = 'rejected'
            record.message_post(body=_('Approval request rejected.'))
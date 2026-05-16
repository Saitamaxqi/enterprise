from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ApprovalActionWizard(models.TransientModel):
    _name = 'approval.action.wizard'
    _description = 'Approval Action Wizard'

    request_id = fields.Many2one(
        'approval.request',
        string='Approval Request',
        required=True
    )

    action_type = fields.Selection([
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
    ], string='Action', required=True)

    comment = fields.Text(string='Comment')

    stage_comment_required = fields.Boolean(
        string='Stage Comment Required',
        compute='_compute_stage_comment_required'
    )

    @api.depends('request_id.stage_id.comment_required')
    def _compute_stage_comment_required(self):
        for wizard in self:
            wizard.stage_comment_required = bool(wizard.request_id.stage_id.comment_required)

    def action_confirm(self):
        self.ensure_one()

        if not self.request_id:
            raise UserError(_('No approval request found.'))

        comment = (self.comment or '').strip()

        if self.action_type == 'rejected' and not comment:
            raise UserError(_('A comment is required when rejecting a request.'))

        if self.action_type == 'approved' and self.request_id.stage_id.comment_required and not comment:
            raise UserError(_('A comment is required for approval at this stage.'))

        if self.action_type == 'approved':
            self.request_id.action_approve(comment)
        elif self.action_type == 'rejected':
            self.request_id.action_reject(comment)
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Records'),
            'res_model': self.request_id.res_model,
            'view_mode': 'list,form',
            'target': 'current',
        }
from odoo import models, fields


class ApprovalLog(models.Model):
    _name = 'approval.log'
    _description = 'Approval Log'
    _order = 'action_date desc, id desc'

    request_id = fields.Many2one(
        'approval.request',
        string='Approval Request',
        required=True,
        ondelete='cascade'
    )

    user_id = fields.Many2one(
        'res.users',
        string='Action By',
        required=True,
        readonly=True,
        ondelete='cascade',
        default=lambda self: self.env.user
    )

    action = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Action', required=True, readonly=True)

    action_date = fields.Datetime(
        string='Action Date',
        default=fields.Datetime.now,
        required=True,
        readonly=True
    )

    comment = fields.Text(string='Comment')
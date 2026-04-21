from odoo import models, fields, api
from odoo.exceptions import UserError

class AssetMoveHistory(models.Model):
    _name = 'asset.move.history'
    _description = 'Asset Move History'

    asset_id = fields.Many2one('account.asset', required=True)  

    from_employee_id = fields.Many2one('hr.employee', readonly=False)
    to_employee_id = fields.Many2one('hr.employee', required=True)

    from_location_id = fields.Many2one('asset.location', readonly=False)
    to_location_id = fields.Many2one('asset.location', required=True)

    moved_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    move_date = fields.Datetime(string="Move Date", default=fields.Datetime.now)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Approval'),
        ('assigned', 'Assigned'),
        ('declined', 'Declined')
    ], default='draft')

    is_current_user = fields.Boolean(compute="_compute_is_current_user")

    # Link to approval workflow requests
    workflow_request_ids = fields.One2many(
        'approval.request',
        'asset_move_id',
        string="Approval Requests"
    )

    @api.depends('to_employee_id')
    def _compute_is_current_user(self):
        for rec in self:
            rec.is_current_user = (
                rec.to_employee_id.user_id == rec.env.user if rec.to_employee_id else False
            )

    def action_submit_for_approval(self):
        """Create an approval request linked to this move"""
        for rec in self:
            workflow = self.env['approval.workflow'].search([
                ('model_id.model', '=', 'asset.move.history')
            ], limit=1)

            if not workflow:
                raise UserError("No workflow defined for Asset Move History.")

            self.env['approval.request'].create({
                'workflow_id': workflow.id,
                'res_model': 'asset.move.history',
                'res_id': rec.id,
                'asset_move_id': rec.id,
                'requester_id': self.env.user.id,
            })

            rec.state = 'waiting'

    def set_assigned(self):
        for rec in self:
            if rec.to_employee_id.user_id != self.env.user:
                raise UserError("You are not allowed to approve this move.")
            rec.state = 'assigned'
            if rec.asset_id:
                rec.asset_id.sudo().write({
                    'employee_id': rec.to_employee_id.id,
                    'location_id': rec.to_location_id.id,
                })

    def set_declined(self):
        for rec in self:
            if rec.to_employee_id.user_id != self.env.user:
                raise UserError("You are not allowed to decline this move.")
            rec.state = 'declined'

    @api.onchange('asset_id')
    def _onchange_asset(self):
        if self.asset_id:
            self.from_employee_id = self.asset_id.employee_id
            self.from_location_id = self.asset_id.location_id

    @api.constrains('to_employee_id', 'asset_id')
    def _check_to_employee_not_current(self):
        for rec in self:
            if (
                rec.asset_id and rec.asset_id.employee_id and rec.to_employee_id
                and rec.to_employee_id == rec.asset_id.employee_id
            ):
                raise UserError("The selected employee is already assigned to this asset.")

    def action_open_approval_requests(self):
        """Open related approval requests in form view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Requests',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('asset_move_id', '=', self.id)],
            'context': {'default_asset_move_id': self.id},
        }

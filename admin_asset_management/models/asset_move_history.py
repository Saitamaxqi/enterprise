from odoo import models, fields, api
from odoo.exceptions import UserError


class AssetMoveHistory(models.Model):
    _name = 'asset.move.history'
    _description = 'Asset Move History'

    asset_id = fields.Many2one('account.asset', required=True,readonly=True)

    from_employee_id = fields.Many2one('hr.employee',readonly=True)
    to_employee_id = fields.Many2one('hr.employee',required=True)

    from_location_id = fields.Many2one('asset.location',readonly=True)
    to_location_id = fields.Many2one('asset.location',required=True)

    moved_by = fields.Many2one('res.users', default=lambda self: self.env.user,readonly=True)
    move_date = fields.Datetime(
        string="Move Date",
        default=fields.Datetime.now)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('declined', 'Declined')
    ], default='draft')
    is_current_user = fields.Boolean(
    compute="_compute_is_current_user"
)

    @api.depends('to_employee_id')
    def _compute_is_current_user(self):
        for rec in self:
            rec.is_current_user = rec.to_employee_id.user_id == self.env.user

    def set_assigned(self):
        for rec in self:
            if rec.to_employee_id.user_id != self.env.user:
                raise UserError("You are not allowed to approve this move.")
            rec.state = 'assigned'
            if rec.asset_id:
                rec.asset_id.employee_id = rec.to_employee_id
                rec.asset_id.location_id = rec.to_location_id
    
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
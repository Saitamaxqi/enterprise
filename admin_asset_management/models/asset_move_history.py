from odoo import models, fields


class AssetMoveHistory(models.Model):
    _name = 'asset.move.history'
    _description = 'Asset Move History'

    asset_id = fields.Many2one('account.asset', required=True)

    previous_employee_id = fields.Many2one('hr.employee')
    current_employee_id = fields.Many2one('hr.employee')

    previous_location_id = fields.Many2one('asset.location')
    current_location_id = fields.Many2one('asset.location')

    moved_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    move_date = fields.Datetime(
        string="Move Date",
        default=fields.Datetime.now)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('declined', 'Declined')
    ], default='draft')

    def set_assigned(self):
        for rec in self:
            rec.state = 'assigned'

            if rec.asset_id:
                rec.asset_id.employee_id = rec.current_employee_id.id
    
    def set_declined(self):
        for rec in self:
            rec.state = 'declined'
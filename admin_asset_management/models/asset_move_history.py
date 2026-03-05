from odoo import models, fields

class AssetMoveHistory(models.Model):
    _name = 'asset.move.history'
    _description = 'Asset Move History'

    asset_id = fields.Many2one(
        'account.asset',
        string="Asset",
        required=True
    )

    previous_employee_id = fields.Many2one(
        'hr.employee',
        string="Previous Employee"
    )

    current_employee_id = fields.Many2one(
        'hr.employee',
        string="Current Employee"
    )

    previous_location_id = fields.Many2one(
        'asset.location',
        string="Previous Location"
    )

    current_location_id = fields.Many2one(
        'asset.location',
        string="Current Location"
    )

    moved_by = fields.Many2one(
        'res.users',
        string="Moved By"
    )

    move_date = fields.Datetime(
        string="Move Date",
        default=fields.Datetime.now
    )
from odoo import models, fields

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Assigned Employee"
    )

    location_id = fields.Many2one(
        'asset.location',
        string="Asset Location"
    )

    move_history_ids = fields.One2many(
        'asset.move.history',
        'asset_id',
        string="Move History"
    )
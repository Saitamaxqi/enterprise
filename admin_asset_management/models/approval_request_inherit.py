from odoo import models,fields

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    asset_move_id = fields.Many2one(
        'asset.move.history',
        string="Asset Move",
        ondelete='cascade'
    )
from odoo import models, fields

class AssetReturnChecklist(models.Model):
    _name = 'asset.return.checklist'
    _description = 'Asset Return Checklist'

    asset_id = fields.Many2one('account.asset', required=True, ondelete='cascade')
    item_name = fields.Char(string="Item", required=True)
    is_returned = fields.Boolean(string="Returned", default=False)

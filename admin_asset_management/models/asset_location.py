from odoo import models, fields

class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = 'Asset Location'

    name = fields.Char(string="Location Name", required=True)
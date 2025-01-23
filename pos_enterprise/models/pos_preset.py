from odoo import models, api


class PosPreset(models.Model):
    _inherit = "pos.preset"

    @api.model
    def _load_pos_preparation_data_fields(self):
        return ['name']

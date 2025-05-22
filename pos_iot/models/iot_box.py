# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class IotBox(models.Model):
    _name = 'iot.box'
    _inherit = ['iot.box', 'pos.load.mixin']

    associated_pos_config_ids = fields.Many2many(
        'pos.config', string="Associated PoS", compute='_compute_associated_pos_config_ids'
    )

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', [device['iot_id'] for device in data['iot.device'] if device['iot_id']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['ip', 'name']

    @api.depends('device_ids')
    def _compute_associated_pos_config_ids(self):
        """Compute the associated PoS config ids for the IoT Box."""
        for box in self:
            domain = expression.OR([
                [('iface_printer_id', 'in', box.device_ids.ids)],
                [('iface_display_id', 'in', box.device_ids.ids)],
                [('iface_scale_id', 'in', box.device_ids.ids)],
                [('iface_scanner_ids', 'in', box.device_ids.ids)],
            ])
            domain = expression.AND([
                [('is_posbox', '=', True)],
                domain
            ])
            box.associated_pos_config_ids = self.env['pos.config'].search(domain)

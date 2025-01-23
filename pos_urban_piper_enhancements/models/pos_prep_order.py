from odoo import models, fields, api
from odoo.tools.json import scriptsafe as json


class PosPrepOrder(models.Model):
    _inherit = 'pos.prep.order'

    delivery_datetime = fields.Char(compute='_compute_delivery_datetime')

    @api.depends('pos_order_id.delivery_json')
    def _compute_delivery_datetime(self):
        for order in self:
            order.delivery_datetime = json.loads(order.pos_order_id.delivery_json).get('order', {}).get('details', {}).get('delivery_datetime', 0) if order.pos_order_id.delivery_json else ''

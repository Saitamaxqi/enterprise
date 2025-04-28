# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController

class PosSelfOrderPreparationDisplayController(PosSelfOrderController):
    @http.route()
    def process_order(self, order, access_token, table_identifier, device_type):
        res = super().process_order(order, access_token, table_identifier, device_type)
        self._send_to_preparation_display(res['pos.order'][0]['id'])
        return res

    @http.route()
    def change_printer_status(self, access_token, has_paper):
        super().change_printer_status(access_token, has_paper)
        pos_config = self._verify_pos_config(access_token)
        pos_config.env['pos.prep.display']._paper_status_change(pos_config)

    def _send_to_preparation_display(self, pos_order_id):
        """ Send paid orders to the preparation display. """
        pos_order = http.request.env['pos.order'].browse(pos_order_id)
        if pos_order.config_id.self_ordering_mode in ['kiosk', 'mobile'] and pos_order.state == 'paid':
            pos_order.env['pos.prep.order'].sudo().process_order(pos_order.id)

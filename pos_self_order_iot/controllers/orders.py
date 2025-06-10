from odoo import http, fields
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfOrderControllerIot(PosSelfOrderController):

    @http.route("/pos-self-order/iot-payment-cancelled/", auth="public", type="jsonrpc", website=True)
    def iot_payment_cancelled(self, access_token, order_id):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env["pos.order"].search([("id", "=", order_id), ("config_id", "=", pos_config.id)])
        order._send_payment_result('fail')

    @http.route("/pos-self-order/iot-payment-success/", auth="public", type="jsonrpc", website=True)
    def iot_payment_success(self, access_token, order_id, payment_method_id, payment_info):
        pos_config = self._verify_pos_config(access_token)
        payment_method = pos_config.payment_method_ids.filtered(lambda p: p.id == payment_method_id)
        order = pos_config.env["pos.order"].search([("id", "=", order_id), ("config_id", "=", pos_config.id)])
        order.add_payment({
            "amount": order.amount_total,
            "payment_date": fields.Datetime.now(),
            "payment_method_id": payment_method.id,
            "card_type": payment_info["Card"],
            "transaction_id": str(payment_info["PaymentTransactionID"]),
            "payment_status": "Success",
            "ticket": payment_info["Ticket"],
            "pos_order_id": order.id
        })

        order.action_pos_order_paid()

        if order.config_id.self_ordering_mode == "kiosk":
            order._send_payment_result('Success')

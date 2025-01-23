from odoo import models


class PosPrepDisplay(models.Model):
    _inherit = "pos.prep.display"

    def _get_pos_orders(self):
        self.ensure_one()
        if len(self.stage_ids) <= 1:
            return {"done": [], "notDone": []}
        last_stage = self.stage_ids[-1]  # last stage always means that the order is done.
        second_last_stage = self.stage_ids[-2]  # order will be displated as ready.

        orders_completed = set()
        orders_not_completed = set()
        pdis_line_ids = self._get_open_orderlines_in_display().filtered(lambda o: o.stage_id != last_stage)

        for pdis_line_id in pdis_line_ids:
            order_stage_id = pdis_line_id.stage_id
            pos_order_tracking_ref = pdis_line_id.prep_line_id.prep_order_id.pos_order_id.tracking_number
            unfinished_pdis_orders = (
                (
                    line.prep_line_id.prep_order_id.pos_order_id == pdis_line_id.prep_line_id.prep_order_id.pos_order_id
                    and line.stage_id != second_last_stage
                    and pdis_line_id != line
                )
                for line in pdis_line_ids
            )
            if order_stage_id == second_last_stage and not any(unfinished_pdis_orders):
                orders_completed.add(pos_order_tracking_ref)
            elif order_stage_id != last_stage:
                orders_not_completed.add(pos_order_tracking_ref)
        return {
            "done": list(orders_completed),
            "notDone": list(orders_not_completed),
        }

    def _send_orders_to_customer_display(self):
        self.ensure_one()
        orders = self._get_pos_orders()
        self._notify("NEW_ORDERS", orders)

    def _send_load_orders_message(self, sound=False, notification=None, orderId=None):
        super()._send_load_orders_message(sound, notification, orderId)
        self._send_orders_to_customer_display()

    def open_customer_display(self):
        return {
            "type": "ir.actions.act_url",
            "url": f"/pos-order-tracking?access_token={self.access_token}",
            "target": "new",
        }

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def write(self, vals):
        if 'state' in vals:
            for purchase_order in self:
                purchase_order._log_po_state_change_to_approval_request_chatter(purchase_order.state, vals['state'])
        return super().write(vals)

    def _log_po_state_change_to_approval_request_chatter(self, old_state, new_state):
        self.ensure_one()
        if old_state == new_state:
            return
        related_product_lines_by_approval_request = self.sudo().env['approval.product.line'].search([
            ('purchase_order_line_id.order_id', '=', self.id)
        ]).grouped('approval_request_id')
        for approval_request, product_lines in related_product_lines_by_approval_request.items():
            state_change_msg = self._create_state_change_msg(old_state, new_state, product_lines)
            approval_request._message_log(body=state_change_msg)

    def _create_state_change_msg(self, old_state, new_state, approval_request_products):
        state_label = dict(self._fields['state']._description_selection(self.env))
        return Markup("%(state_change_header)s<br> %(products_summary)s") % {
            'state_change_header': _("RFQ %(rfq_name)s state has been changed: %(old_state_label)s -> %(new_state_label)s",
                rfq_name=self.name,
                old_state_label=state_label[old_state],
                new_state_label=state_label[new_state]),
            'products_summary': Markup("%(header)s<br> <ul>%(products)s</ul>") % {
                'header': _("Products: "),
                'products': Markup().join(
                    Markup("<li>%(product_quantity)s %(product_name)s</li>") % {
                        'product_quantity': product.quantity,
                        'product_name': product.product_id.name
                    } for product in approval_request_products
                )
            }
        }

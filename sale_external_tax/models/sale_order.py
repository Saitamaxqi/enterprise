# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['account.external.tax.mixin', 'sale.order']

    def action_confirm(self):
        """ Ensure confirmed orders have the right taxes. """
        self._get_and_set_external_taxes_on_eligible_records()
        return super().action_confirm()

    def action_quotation_send(self):
        """ Calculate taxes before presenting order to the customer. """
        self._get_and_set_external_taxes_on_eligible_records()
        return super().action_quotation_send()

    def _get_and_set_external_taxes_on_eligible_records(self):
        """ account.external.tax.mixin override. """
        eligible_orders = self.filtered(
            lambda order: order.is_tax_computed_externally and order._get_lines_eligible_for_external_taxes() and
                          order.state in ('draft', 'sent', 'sale') and not order.locked
        )
        eligible_orders._set_external_taxes(eligible_orders._get_external_taxes())
        return super()._get_and_set_external_taxes_on_eligible_records()

    def _get_lines_eligible_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)

    def _get_line_data_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        res = []
        for line in self._get_lines_eligible_for_external_taxes():
            res.append({
                "id": line.id,
                "model_name": line._name,
                "product_id": line.product_id,
                "description": line.name,
                "qty": line.product_uom_qty,
                "uom_id": line.product_uom_id,
                "price_subtotal": line.price_subtotal,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "is_refund": False,
            })

        return res

    def _get_date_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.date_order

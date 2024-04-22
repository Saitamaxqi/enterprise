# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderOption(models.Model):
    _inherit = 'sale.order.option'

    order_is_rental = fields.Boolean(related='order_id.is_rental_order', depends=['order_id'])

    def add_option_to_order(self):
        """ Override to add the rental context so that new SOL can be flagged as rental """
        if self.order_id.is_rental_order:
            self = self.with_context(in_rental_app=True)
        return super().add_option_to_order()

    def _get_values_to_add_to_order(self):
        """ Override to remove the name and force its recomputation to add the period on the SOL """
        vals = super()._get_values_to_add_to_order()
        if self.order_id.is_rental_order and self.product_id.rent_ok:
            vals.pop('name')
        return vals

    @api.model
    def _domain_product_id(self):
        """ Override to allow users to add a rental product if the order is a rental one """
        super_part = ','.join(str(leaf) for leaf in super()._domain_product_id())
        return f"['|', ('rent_ok', '=', order_is_rental), {super_part}]"

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_add(self, product_id, quantity=1.0, *, plan_id=None, **kwargs):
        product = self.env['product.product'].browse(product_id)
        if product.recurring_invoice and not kwargs.get('allow_one_time_sale'):
            if plan_id and self.plan_id and self.plan_id.id != plan_id:
                raise UserError(_("You cannot mix different subscription plans in the same order."))

            if not self.plan_id:
                self.plan_id = (
                    self.env['sale.subscription.plan'].browse(plan_id and int(plan_id)).exists()
                    or self.env['sale.subscription.pricing'].sudo()._get_first_suitable_recurring_pricing(
                        product,
                        pricelist=self.pricelist_id
                    ).plan_id
                )

        return super()._cart_add(product_id, quantity, plan_id=plan_id, **kwargs)

    def _verify_cart_after_update(self, *args, **kwargs):
        super()._verify_cart_after_update(*args, **kwargs)
        if not self.order_line.filtered(lambda sol: sol.product_id.recurring_invoice):
            self.plan_id = False

    def allow_one_time_purchase(self):
        """Check if the sale order contains a one-time purchase product."""
        return any(
            not line.order_id.plan_id
            and line.product_id.recurring_invoice
            and line.product_id.allow_one_time_sale
            for line in self.order_line)

    def _show_all_pricing(self):
        if not self or not self.order_line or (not self.plan_id and not self.order_line.filtered(lambda sol: sol.product_id.recurring_invoice)):
            return "both"
        elif self.plan_id:
            return "recurring"
        elif not self.plan_id:
            return "onetime"

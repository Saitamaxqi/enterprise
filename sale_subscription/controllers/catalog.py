# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.product.controllers.catalog import ProductCatalogController

class SubscriptionProductCatalogController(ProductCatalogController):

    @route()
    def product_catalog_get_order_lines_info(self, res_model, order_id, product_ids, **kwargs):
        """
        Returns subscription products information to be shown in the catalog.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :rtype: dict
        :return: A dict with the following structure:
            {
                product.id: {
                    'productId': int,
                    'quantity': float (optional),
                    'price': float,
                    'readOnly': bool (optional)
                }
            }
        """
        res = super().product_catalog_get_order_lines_info(res_model, order_id, product_ids, **kwargs)
        order = request.env['sale.order'].browse(order_id).exists()
        if not order or not order.plan_id:
            return res

        products = request.env['product.product'].search([('id', 'in', product_ids)])
        for product in products + order.order_line.product_id:
            if not res.get(product.id) or not product.recurring_invoice:
                continue
            subscription_product_pricing = product.product_tmpl_id._get_pricing(
                order.pricelist_id, variant=product, plan_id=order.plan_id.id
            )
            if subscription_product_pricing:
                res[product.id]['price'] = subscription_product_pricing.fixed_price
                res[product.id]['plan_name'] = subscription_product_pricing.plan_id.name
        return res

    @route()
    def product_catalog_update_order_line_info(self, res_model, order_id, product_id, quantity=0, **kwargs):
        """
        Update order line information on a given order for a given subscription product.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param int product_id: The product, as a `product.product` id.
        :return: The unit price of the product, based on the pricelist of the order and
                 the quantity selected.
        :rtype: float
        """
        res = super().product_catalog_update_order_line_info(res_model, order_id, product_id, quantity=quantity, **kwargs)

        order = request.env['sale.order'].browse(order_id).exists()
        if not order:
            return res
        product = request.env['product.product'].browse(product_id).exists()
        if not product or not product.recurring_invoice:
            return res
        if not order.plan_id:
            return product.lst_price
        subscription_product_pricing = product.product_tmpl_id._get_pricing(
            order.pricelist_id, variant=product, plan_id=order.plan_id.id
        )
        if subscription_product_pricing:
            return subscription_product_pricing.fixed_price
        return res

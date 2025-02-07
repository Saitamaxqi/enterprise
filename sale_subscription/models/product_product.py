# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_subscription_pricing_ids = fields.One2many(
        string="Custom Subscription Pricings",
        comodel_name='product.pricelist.item',
        inverse_name='product_id',
        compute='_compute_product_subscription_pricing_ids',
        readonly=False,
    )

    @api.depends('product_tmpl_id')
    def _compute_product_subscription_pricing_ids(self):
        for product in self:
            if not product.id:
                product.product_subscription_pricing_ids = False
                continue
            product.product_subscription_pricing_ids = product.product_tmpl_id.product_subscription_pricing_ids.filtered(
                lambda rule: not rule.product_id or rule.product_id == product.id
            )

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from math import floor

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import format_amount


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('optional_product_ids')
    def _constraints_optional_product_ids(self):
        for template in self:
            if not template.recurring_invoice:
                continue
            plan_ids = set(template.product_subscription_pricing_ids.plan_id.ids)
            for optional_template in template.optional_product_ids:
                if not optional_template.recurring_invoice:
                    continue
                optional_plan_ids = optional_template.product_subscription_pricing_ids.plan_id.ids
                if not plan_ids.intersection(optional_plan_ids):
                    raise UserError(_('You cannot have an optional product that has a no common pricing\'s plan.'))

    def _website_can_be_added(self, product=None) -> bool:
        """Return whether the product/template can be added to the active SO."""
        self.ensure_one()
        if not self.recurring_invoice:
            return True

        has_pricing = bool(
            self._get_recurring_pricing(
                pricelist=request.pricelist,
                variant=product,
                plan_id=request.cart.plan_id.id,
            )
        )
        return has_pricing or (
            self.allow_one_time_sale
            and self.type == 'consu'
            and not request.cart.plan_id
        )

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        if not product_or_template.recurring_invoice:
            return res

        product = (product_or_template.is_product_variant and product_or_template) or self.env['product.product']
        pricings = self._get_recurring_pricings(pricelist=request.pricelist, variant=product)

        res['list_price'] = res['price']  # No pricelist discount for subscription prices
        currency = website.currency_id
        requested_plan = request and request.params.get('plan_id')
        requested_plan_id = requested_plan and requested_plan.isdigit() and int(requested_plan)
        possible_pricing_count = 0

        if pricings:
            to_year = {'year': 1, 'month': 12, 'week': 52}
            translation_mapping = {
                'year': _('year'),
                'month': _('month'),
                'week': _('week'),
            }
            minimum_period = min(
                pricings.sudo().plan_id.mapped('billing_period_unit'),
                key=lambda x: 1 / to_year[x],
            )

        if not pricings:
            res.update({
                'is_subscription': True,
                'is_plan_possible': False,
                'pricings': False,
                'allow_one_time_sale': self.allow_one_time_sale,
                'show_all_pricing': request.cart._show_all_pricing(),
            })
            return res

        pricing_details = []
        default_pricing_data = {}
        for pricing in pricings:
            price = pricing._compute_price(
                product=product_or_template,
                quantity=quantity or 1.0,
                date=date,
                uom=product_or_template.uom_id,  # TODO VFE website uom broll when merged
                currency=currency,
            )

            if res.get('product_taxes', False):
                price = self.env['product.template']._apply_taxes_to_price(
                    price, currency, res['product_taxes'], res['taxes'], product_or_template,
                )

            price_format = format_amount(self.env, amount=price, currency=currency)
            pricing_plan_sudo = pricing.plan_id.sudo()  # Not accessible to public users
            price_in_minimum_period = (
                price
                / pricing_plan_sudo.billing_period_value
                * to_year[pricing_plan_sudo.billing_period_unit]
                / to_year[minimum_period]
            )
            can_be_added = request.cart.plan_id.id in (pricing_plan_sudo.id, False)
            pricing_data = {
                'plan_id': pricing_plan_sudo.id,
                'price': f"{pricing.plan_id.name}: {price_format}",
                'price_value': price,
                'table_price': price_format,
                'table_name': pricing.plan_id.name.replace(' ', ' '),
                'to_minimum_billing_period': f'{format_amount(self.env, amount=price_in_minimum_period, currency=currency)}'
                                             f' / {translation_mapping.get(minimum_period, minimum_period)}',
                'can_be_added': can_be_added,
            }
            if can_be_added:
                possible_pricing_count += 1
                if (not default_pricing_data or pricing_plan_sudo.id == requested_plan_id):
                    default_pricing_data = pricing_data

            # discount calculation for one time purchase
            discount = 0.0
            if product_or_template.type == 'consu':
                if price > 0 and self.list_price > 0 and self.list_price >= price:
                    discount = ((self.list_price - price) * 100) / self.list_price
                    pricing_data['discounted_price'] = floor(discount)  # Round down to the nearest integer
                else:
                    pricing_data['discounted_price'] = 0.0

            pricing_details.append(pricing_data)

        unit_price = default_pricing_data.get('price_value', 0)
        return {
            **res,
            'is_subscription': True,
            'pricings': pricing_details,
            'is_plan_possible': possible_pricing_count > 0,
            'price': unit_price,
            'subscription_default_pricing_price': default_pricing_data.get('price', ''),
            'subscription_default_pricing_plan_id': default_pricing_data.get('plan_id', False),
            'subscription_pricing_select': possible_pricing_count > 1,
            'prevent_zero_price_sale': website.prevent_zero_price_sale and currency.is_zero(
                unit_price,
            ),
            'allow_one_time_sale': self.allow_one_time_sale,
            'product_type': self.type,
            'show_all_pricing': request.cart._show_all_pricing(),
            'currency_symbol': self.env.company.currency_id.symbol
        }

    # Search bar
    def _search_render_results_prices(self, mapping, combination_info):
        if not combination_info.get('is_subscription'):
            return super()._search_render_results_prices(mapping, combination_info)

        if not combination_info['is_plan_possible']:
            return '', 0

        return self.env['ir.ui.view']._render_template(
            'website_sale_subscription.subscription_search_result_price',
            values={
                'subscription_default_pricing_price': combination_info['subscription_default_pricing_price'],
            }
        ), 0

    def _get_sales_prices(self, website):
        prices = super()._get_sales_prices(website)

        pricelist = request.pricelist
        currency = website.currency_id
        fiscal_position_sudo = request.fiscal_position
        so_plan_id = request.cart.plan_id.id
        date = fields.Date.context_today(self)

        for template in self:
            if not template.recurring_invoice:
                continue

            pricing = template._get_recurring_pricing(pricelist=pricelist, plan_id=so_plan_id)
            if not pricing:
                prices[template.id].update({
                    'is_subscription': True,
                    'is_plan_possible': False,
                })
                continue

            unit_price = pricing._compute_price(
                product=template,
                quantity=1.0,
                date=date,
                uom=template.uom_id,  # TODO VFE website uom broll when merged
                currency=currency,
            )

            # taxes application
            product_taxes = template.sudo().taxes_id.filtered(lambda t: t.company_id == t.env.company)
            if product_taxes:
                taxes = fiscal_position_sudo.map_tax(product_taxes)
                unit_price = self.env['product.template']._apply_taxes_to_price(
                    unit_price, currency, product_taxes, taxes, template)

            plan_sudo = pricing.plan_id.sudo()
            prices[template.id].update({
                'is_subscription': True,
                'price_reduce': unit_price,
                'is_plan_possible': True,  # The plan can only be valid at this point
                'temporal_unit_display': plan_sudo.billing_period_display_sentence,
            })

        return prices

    def _website_show_quick_add(self):
        self.ensure_one()
        return super()._website_show_quick_add() and self._website_can_be_added()

    def _can_be_added_to_cart(self):
        self.ensure_one()
        return super()._can_be_added_to_cart() and self._website_can_be_added()

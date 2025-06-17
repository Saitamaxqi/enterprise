# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request, route
from odoo.tools.intervals import Intervals

from odoo.addons.website_sale_renting.controllers.main import WebsiteSaleRenting


class WebsiteSalePlanningRenting(WebsiteSaleRenting):

    @route()
    def renting_product_availabilities(self, product_id, min_date, max_date):
        product_sudo = request.env['product.product'].sudo().browse(product_id).exists()
        result = super().renting_product_availabilities(product_id, min_date, max_date)
        if (
            product_sudo.type == 'service'
            and product_sudo.rent_ok
            and product_sudo.planning_enabled
            and (resources := product_sudo.planning_role_id.filtered('sync_shift_rental').resource_ids)
        ):
            min_date = fields.Datetime.to_datetime(min_date)
            max_date = fields.Datetime.to_datetime(max_date)
            slots = self.env['planning.slot'].search([
                ('resource_id', 'in', resources.ids),
                ('start_datetime', '<=', max_date),
                ('end_datetime', '>=', min_date),
            ])
            intervals = Intervals([
                (
                    max(min_date, slot.start_datetime),
                    min(max_date, slot.end_datetime),
                    slot
                )
                for slot in slots
            ])
            availabilities = []
            for start, end, shifts in intervals:
                availabilities.append({
                    'start': start,
                    'end': end,
                    'quantity_available': len(resources) - len(shifts.resource_id),
                })
            result['renting_availabilities'] = availabilities
        return result

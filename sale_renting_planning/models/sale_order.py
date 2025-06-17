from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        res = super().write(vals)
        rental_start_date = vals.get('rental_start_date')
        rental_return_date = vals.get('rental_return_date')
        if rental_start_date or rental_return_date:
            if rental_orders := self.filtered('is_rental_order'):
                slots = self.env['planning.slot'].search([('sale_order_id', 'in', rental_orders.ids)])
                slots_vals = {}
                if rental_start_date:
                    slots_vals['start_datetime'] = rental_start_date
                if rental_return_date:
                    slots_vals['end_datetime'] = rental_return_date
                slots.write(slots_vals)
        return res

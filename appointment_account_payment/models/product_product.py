# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_product_placeholder_filename(self):
        if self.env['appointment.type'].search_count([('product_id', '=', self.id)], limit=1):
            return 'appointment_account_payment/static/src/img/booking_product.png'
        return super()._get_product_placeholder_filename()

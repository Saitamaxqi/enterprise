from odoo import models, fields, api, _


class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    def get_all_parents(self):
        self.ensure_one()
        parents = self
        while parents.parent_id:
            parents |= parents.parent_id
        return parents

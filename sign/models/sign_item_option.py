# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignItemOption(models.Model):
    _description = "Option of a selection Field"
    _rec_name = "value"

    value = fields.Text(string="Option", readonly=True)
    available = fields.Boolean(string="Available in new templates", default=True)

    _sql_constraints = [
        ('value_uniq', 'unique (value)', "Value already exists!"),
    ]

    @api.model
    def name_create(self, name):
        existing_option = self.search([('value', '=ilike', name.strip())], limit=1)
        if existing_option:
            existing_option.available = True
            return existing_option.id, existing_option.display_name
        return super().name_create(name)

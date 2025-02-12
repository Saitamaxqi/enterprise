# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignItemOption(models.Model):
    _name = 'sign.item.option'
    _description = "Option of a selection Field"
    _rec_name = "value"

    value = fields.Text(string="Option", readonly=True)

    _value_uniq = models.Constraint(
        'unique (value)',
        "Value already exists!",
    )

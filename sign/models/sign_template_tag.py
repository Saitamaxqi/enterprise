# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint
from odoo import fields, models


class SignTemplateTag(models.Model):
    _description = "Sign Template Tag"
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]

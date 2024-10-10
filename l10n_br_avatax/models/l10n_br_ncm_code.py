# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10n_BrNcmCode(models.Model):
    _description = "NCM Code"

    code = fields.Char("Code")
    name = fields.Char("Name")

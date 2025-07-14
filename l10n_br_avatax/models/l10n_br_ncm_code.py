# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10n_BrNcmCode(models.Model):
    _name = 'l10n_br.ncm.code'
    _description = "NCM Code"

    code = fields.Char("Code")
    name = fields.Char("Name")
    ex = fields.Char(
        string="EX",
        help="Brazil: Use this field to indicate an 'EX Citation' which identifies exceptions to Avalara’s standard fiscal rules.\n"
            "EX Citations help define specific tax treatments (e.g., CST, ST, rate reductions, special benefits) for products "
            "with tax behavior different from Avalara’s default settings."
    )

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class L10n_BrNcmCode(models.Model):
    _name = 'l10n_br.ncm.code'
    _description = "NCM Code"
    _rec_names_search = ["code", "name"]

    code = fields.Char("Code", required=True)
    name = fields.Char("Name", required=True)
    ex = fields.Char(
        string="EX",
        help="Brazil: Use this field to indicate an 'EX Citation' which identifies exceptions to Avalara’s standard fiscal rules.\n"
            "EX Citations help define specific tax treatments (e.g., CST, ST, rate reductions, special benefits) for products "
            "with tax behavior different from Avalara’s default settings."
    )

    _name_uniq = models.Constraint(
        'UNIQUE(name, code)',
        'This combination of name and code already exists.',
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for ncm in self:
            ncm.display_name = f"[{ncm.code}] {ncm.name}"

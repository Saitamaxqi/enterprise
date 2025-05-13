# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_be_isoc_corporate_tax_rate = fields.Selection(
        selection=[
            ('25', "25 %"),
            ('20', "20 %"),
        ],
        string="Corporate Tax Rate",
        default='25',
    )

    def _get_countries_allowing_tax_representative(self):
        rslt = super()._get_countries_allowing_tax_representative()
        rslt.add(self.env.ref('base.be').code)
        return rslt

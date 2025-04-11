# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountExternalTaxMixin(models.AbstractModel):
    _inherit = "account.external.tax.mixin"

    def _l10n_br_build_avatax_line(self, product, *args):
        """ Override. Include required fields for EDI. """
        res = super()._l10n_br_build_avatax_line(product, *args)
        res["itemCode"] = product.default_code
        return res

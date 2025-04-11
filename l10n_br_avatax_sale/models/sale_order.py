# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _depends_l10n_br_avatax_warnings(self):
        """account.external.tax.mixin override."""
        return super()._depends_l10n_br_avatax_warnings() + ["order_line"]

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res["l10n_br_cnae_code_id"] = self.l10n_br_cnae_code_id.id
        res["l10n_br_goods_operation_type_id"] = self.l10n_br_goods_operation_type_id.id
        res["l10n_br_use_type"] = self.l10n_br_use_type
        return res

    def _get_line_data_for_external_taxes(self):
        """ Override to set the operation_type per line. """
        res = super()._get_line_data_for_external_taxes()
        for i, line in enumerate(self._get_lines_eligible_for_external_taxes()):
            res[i]['operation_type'] = line.l10n_br_goods_operation_type_id or self.l10n_br_goods_operation_type_id
        return res

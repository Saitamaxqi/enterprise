from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _inverse_foreign_vat(self):
        # EXTENDS account
        super()._inverse_foreign_vat()
        self.env['account.return.type']._generate_or_refresh_all_returns(self.company_id.root_id)

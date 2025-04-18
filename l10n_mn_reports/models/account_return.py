from odoo import api, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'MN':
            self.env.ref('l10n_mn_reports.mn_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_mn_reports.mn_corporate_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt

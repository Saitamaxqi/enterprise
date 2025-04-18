from odoo import api, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'CA':
            self.env.ref('l10n_ca_reports.ca_gsthst_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_ca_reports.ca_pst_bc_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_ca_reports.ca_pst_mb_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_ca_reports.ca_qst_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_ca_reports.ca_pst_sk_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt

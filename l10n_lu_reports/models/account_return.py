from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'LU':
            self.env.ref('l10n_lu_reports.lu_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if return_type_external_id == 'l10n_lu_reports.lu_tax_return_type':
            return date_to + relativedelta(days=15) + relativedelta(months=1)

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

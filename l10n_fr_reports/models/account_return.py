from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'FR':
            self.env.ref('l10n_fr_reports.vat_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if return_type_external_id == 'l10n_fr_reports.vat_return_type':
            return date_to + relativedelta(days=19)

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE
        """ Apply the rounding from the French tax report by adding a line to the end of the query results
            representing the sum of the roundings on each line of the tax report.
        """
        if self.type_external_id == 'l10n_fr_reports.vat_return_type':
            rounding_accounts = {
                'profit': company.l10n_fr_rounding_difference_profit_account_id,
                'loss': company.l10n_fr_rounding_difference_loss_account_id,
            }

            vat_results_summary = [
                ('due', self.env.ref('l10n_fr_account.tax_report_32').id, 'balance'),
                ('due', self.env.ref('l10n_fr_account.tax_report_22').id, 'balance'),
                ('deductible', self.env.ref('l10n_fr_account.tax_report_27').id, 'balance'),
            ]
            return self._vat_closing_entry_results_rounding(company, options, results, rounding_accounts, vat_results_summary)

        return super()._postprocess_vat_closing_entry_results(company, options, results)

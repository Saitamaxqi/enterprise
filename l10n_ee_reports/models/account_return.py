from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'EE':
            self.env.ref('l10n_ee_reports.ee_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)
            self.env.ref('l10n_ee_reports.ee_kmd_inf_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if return_type_external_id == 'l10n_ee_reports.ee_tax_return_type':
            return date_to + relativedelta(days=20)

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE 'account_reports'
        """ Apply the rounding from the Estonian tax report to account for rounding differences between line-level
        tax calculations and the Estonian government's total tax computation (base_amount * tax_rate).
        """
        if self.type_external_id == 'l10n_ee_reports.ee_tax_return_type':
            rounding_accounts = {
                'profit': company.l10n_ee_rounding_difference_profit_account_id,
                'loss': company.l10n_ee_rounding_difference_loss_account_id,
            }

            vat_results_summary = [
                ('due', self.env.ref('l10n_ee.tax_report_line_12').id, 'balance'),
                ('deductible', self.env.ref('l10n_ee.tax_report_line_13').id, 'balance'),
            ]

            return self._vat_closing_entry_results_rounding(company, options, results, rounding_accounts, vat_results_summary)

        return super()._postprocess_vat_closing_entry_results(company, options, results)

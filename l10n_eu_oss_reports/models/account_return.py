from odoo import api, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        # Only do that when instantiating the domestic returns, to avoid double computation in case of multivat
        oss_tax_exists = self.env['account.tax'].search_count([
            ('repartition_line_ids.tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_oss').ids),
            ('type_tax_use', '=', 'sale'),
            ('country_id.code', '=', country_code),
            *self.env['account.tax']._check_company_domain(main_company),
        ], limit=1)
        if oss_tax_exists:
            self.env.ref('l10n_eu_oss_reports.eu_oss_sales_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _get_amount_to_pay_additional_tax_domain(self):
        oss_domain = [('repartition_line_ids', 'any', [('tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_oss').ids)])]

        if self.type_external_id in ('l10n_eu_oss_reports.eu_oss_sales_tax_return_type', 'l10n_eu_oss_reports.eu_oss_imports_tax_return_type'):
            return oss_domain
        else:
            return [*super()._get_amount_to_pay_additional_tax_domain(), '!', *oss_domain]

    def _get_vat_closing_entry_additional_domain(self):
        if self.type_external_id == 'l10n_eu_oss_reports.eu_oss_sales_tax_return_type':
            domain = [
                ('tax_line_id', '!=', False),
                *self.env['l10n_eu_oss.sales.tax.report.handler']._get_oss_custom_domain(),
            ]
            return domain
        elif self.type_external_id == 'l10n_eu_oss_reports.eu_oss_imports_tax_return_type':
            return [
                ('tax_line_id', '!=', False),
                *self.env['l10n_eu_oss.imports.tax.report.handler']._get_oss_custom_domain(),
            ]

        # remove oss taxes from normal closings
        domain = super()._get_vat_closing_entry_additional_domain()
        domain += [('tax_tag_ids', 'not in', self.env.ref('l10n_eu_oss.tag_oss').ids)]
        return domain

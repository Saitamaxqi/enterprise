from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    @api.model
    def _generate_all_returns(self, country_code, main_company, tax_unit=None):
        rslt = super()._generate_all_returns(country_code, main_company, tax_unit=tax_unit)

        if country_code == 'GR':
            self.env.ref('l10n_gr_reports.gr_tax_return_type')._try_create_returns_for_fiscal_year(main_company, tax_unit=tax_unit)

        return rslt


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if return_type_external_id == 'l10n_gr_reports.gr_tax_return_type':
            deadline_date = fields.Date.end_of(date_to + relativedelta(months=1), 'month')
            weekday = deadline_date.weekday()
            if weekday > 4:
                deadline_date += relativedelta(days=4 - weekday)
            return deadline_date

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

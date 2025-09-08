from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if self.type_external_id in {'l10n_lt_reports.vat_return_type', 'l10n_lt_reports.lt_ec_sales_list_return_type'}:
            return date_to + relativedelta(days=25)

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

    def _get_state_fields(self):
        # EXTENDS account_reports
        if self.type_external_id in {'l10n_lt_reports.vat_return_type', 'l10n_lt_reports.lt_ec_sales_list_return_type'}:
            return 'generic_state_review_submit'
        return super()._get_state_field()

    def action_submit(self):
        if self.type_external_id == 'l10n_lt_reports.lt_tax_return_type':
            return self.env['l10n_lt_reports.vat.return.submission.wizard']._open_submission_wizard(self)
        if self.type_external_id == 'l10n_lt_reports.lt_ec_sales_list_return_type':
            return self.env['l10n_lt_reports.ec.sales.list.submission.wizard']._open_submission_wizard(self)
        return super().action_submit()

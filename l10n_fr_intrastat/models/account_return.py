from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        # EXTENDS account_reports
        if return_type_external_id in {
            'l10n_fr_intrastat.l10n_fr_intrastat_goods_return_type',
            'l10n_fr_intrastat.l10n_fr_intrastat_services_return_type',
        }:
            return date_to + relativedelta(days=10)

        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

    def action_submit(self):
        # EXTENDS account_reports
        if self.type_external_id in {
            'l10n_fr_intrastat.l10n_fr_intrastat_goods_return_type',
            'l10n_fr_intrastat.l10n_fr_intrastat_services_return_type',
        }:
            return self.env['l10n_fr_intrastat.intrastat.submission.wizard']._open_submission_wizard(self)

        return super().action_submit()

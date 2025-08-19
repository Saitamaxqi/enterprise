from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        # Extends account_reports
        if return_type_external_id == 'l10n_lt_intrastat.lt_intrastat_goods_return_type':
            return date_to + relativedelta(days=10)
        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

    def action_submit(self):
        # Extends account_reports
        if self.type_external_id == 'l10n_lt_intrastat.lt_intrastat_goods_return_type':
            return self.env['l10n_lt_intrastat.intrastat.goods.submission.wizard']._open_submission_wizard(self)
        return super().action_submit()

    def _generate_submission_attachments(self, options):
        # Extends account_reports
        super()._generate_submission_attachments(options)
        if self.type_external_id == 'l10n_lt_intrastat.lt_intrastat_goods_return_type':
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'lt_intrastat_export_to_xml'))

from odoo import models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def action_submit(self):
        if self.type_external_id == 'l10n_be_intrastat.be_intrastat_goods_return_type':
            return self.env['l10n_be_intrastat.intrastat.goods.submission.wizard']._open_submission_wizard(self)

        return super().action_submit()

    def _generate_submission_attachments(self, options):
        super()._generate_submission_attachments(options)
        if self.type_external_id == 'l10n_be_intrastat.be_intrastat_goods_return_type':
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'be_intrastat_export_to_xml'))
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'be_intrastat_export_to_csv'))

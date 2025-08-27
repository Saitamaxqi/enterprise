from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_in_fetch_vendor_edi_feature_enabled = fields.Boolean(related='company_id.l10n_in_fetch_vendor_edi_feature')

    # enet_batch_payment related fields
    bank_template_id = fields.Many2one('enet.bank.template', string='Bank Template')
    has_enet_payment_method = fields.Boolean(compute='_compute_has_enet_payment_method')
    l10n_in_enet_vendor_batch_payment_feature_enabled = fields.Boolean(related='company_id.l10n_in_enet_vendor_batch_payment_feature')

    @api.depends('outbound_payment_method_line_ids.payment_method_id.code')
    def _compute_has_enet_payment_method(self):
        for journal in self:
            if journal.company_id.l10n_in_enet_vendor_batch_payment_feature:
                journal.has_enet_payment_method = any(
                    payment_method.payment_method_id.code in ['enet_rtgs', 'enet_neft', 'enet_fund_transfer', 'enet_demand_draft']
                    for payment_method in journal.outbound_payment_method_line_ids
                )
            else:
                journal.has_enet_payment_method = False

    def l10n_in_action_fetch_irn_data_for_account_journal(self):
        """ Fetch the GST return period for the current company and return the corresponding form view. """
        process_return_period = self.env['l10n_in.gst.return.period']._get_gst_return_period(self.company_id, create_if_not_found=True)
        return process_return_period.open_gst_return_period_form_view()

from odoo import models, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if self.env.user.has_group('account.group_account_readonly') or self.env.user.has_group('account.group_account_invoice'):
            data += ['account.move']
        data += ['ir.ui.view']
        return data

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        res = super().close_session_from_ui(bank_payment_method_diff_pairs=bank_payment_method_diff_pairs)
        if res['successful']:
            settled_invoice_ids = self.order_ids.mapped('lines.settled_invoice_id')
            for inv in settled_invoice_ids:
                # Assign outstanding credits created in the session to the invoice
                for out_cred in inv.invoice_outstanding_credits_debits_widget['content']:
                    if out_cred['journal_name'] == self.name:
                        lines = self.env['account.move.line'].browse(out_cred['id'])
                        lines += inv.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                        lines.reconcile()
        return res

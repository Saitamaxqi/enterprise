from odoo import models


class AccountBankStatementLine(models.Model):
    _name = 'account.bank.statement.line'
    _inherit = 'account.bank.statement.line'

    def set_batch_payment_bank_statement_line(self, batch_payment_id):
        self.ensure_one()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_id)

        amls_domain = self._get_default_amls_matching_domain()
        amls_to_create = batch_payment._get_amls_from_batch_payments(amls_domain)
        self._add_move_line_to_statement_line_move(amls_to_create)
        if payments_to_validate := batch_payment.payment_ids.filtered(lambda p: not p.move_id and p.state in batch_payment._valid_payment_states()):
            payments_to_validate.action_validate()

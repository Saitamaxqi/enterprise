from odoo import models


class AccountBankStatementLine(models.Model):
    _name = 'account.bank.statement.line'
    _inherit = 'account.bank.statement.line'

    def set_batch_payment_bank_statement_line(self, batch_payment_id):
        self.ensure_one()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_id)

        amls_domain = self._get_default_amls_matching_domain()
        # Thanks to a constraint, we cannot have a batch that have payment with and without entries.
        # Batch of payment with entries means that reconciled_lines and amls_to_create will have the same length
        # otherwise reconciled_lines is empty
        reconciled_lines, amls_to_create = batch_payment._get_amls_from_batch_payments(amls_domain)
        has_exchange_diff = False
        if reconciled_lines:
            for reconciled_line, aml_to_create in zip(reconciled_lines, amls_to_create):
                exchange_diff_balance = self._lines_get_account_balance_exchange_diff(reconciled_line.currency_id, reconciled_line.amount_residual, reconciled_line.amount_residual_currency)
                has_exchange_diff = has_exchange_diff or not reconciled_line.currency_id.is_zero(exchange_diff_balance)
                new_balance = -(reconciled_line.amount_residual + exchange_diff_balance)

                aml_to_create['balance'] = new_balance

        self.with_context(no_exchange_difference_no_recursive=not has_exchange_diff)._add_move_line_to_statement_line_move(amls_to_create)
        if payments_to_validate := batch_payment.payment_ids.filtered(lambda p: not p.move_id and p.state in batch_payment._valid_payment_states()):
            payments_to_validate.action_validate()

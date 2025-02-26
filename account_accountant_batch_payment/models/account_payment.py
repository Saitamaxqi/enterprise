from collections import defaultdict

from odoo import models


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'

    def _get_amls_for_payment_without_move(self):
        valid_payment_states = self.env['account.batch.payment']._valid_payment_states()
        lines_to_create = []
        for payment in self:
            if payment.state not in valid_payment_states:
                continue

            account2amount = defaultdict(float)

            payment_term_lines = payment.invoice_ids.line_ids.filtered(lambda line: line.display_type == "payment_term").sorted("date")
            remaining = payment.amount_signed
            for line in payment_term_lines:
                if not remaining:
                    break

                current = min(remaining, line.currency_id._convert(from_amount=line.amount_currency, to_currency=payment.currency_id))
                remaining -= current
                account2amount[line.account_id] -= current

            if remaining:
                account2amount[payment.partner_id.property_account_receivable_id] -= remaining

            for account, amount in account2amount.items():
                # TODO flg keep invoice link here
                lines_to_create.append({
                    'sequence': len(lines_to_create) + 1,
                    'name': payment.name,
                    'account_id': account.id,
                    'partner_id': payment.partner_id.id,
                    'currency_id': payment.currency_id.id,
                    'amount_currency': amount,
                    'balance': payment.currency_id._convert(from_amount=amount, to_currency=self.env.company.currency_id),
                })
        return lines_to_create

from collections import defaultdict

from odoo import Command, models


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'

    def _get_amls_for_payment_without_move(self):
        valid_payment_states = self.env['account.batch.payment']._valid_payment_states()
        lines_to_create = []
        for payment in self:
            if payment.state not in valid_payment_states:
                continue

            line2amount = defaultdict(float)

            payment_term_lines = payment.invoice_ids.line_ids.filtered(lambda line: line.display_type == "payment_term").sorted("date")
            remaining = payment.amount_signed
            for line in payment_term_lines:
                if not remaining:
                    break

                current = min(remaining, line.currency_id._convert(from_amount=line.amount_currency, to_currency=payment.currency_id))
                remaining -= current
                line2amount[line] -= current

            if remaining:
                line2amount[False] -= remaining

            for line, amount in line2amount.items():
                if line:
                    line_to_create = line._get_aml_values(
                        name=payment.name,
                        balance=payment.currency_id._convert(from_amount=amount, to_currency=self.env.company.currency_id),
                        amount_currency=amount,
                        reconciled_lines_ids=[Command.set(line.ids)],
                        payment_lines_ids=[Command.set(payment.ids)],
                    )
                else:
                    partner_account = (
                        payment.partner_id.property_account_payable_id
                        if payment.payment_type == "outbound"
                        else payment.partner_id.property_account_receivable_id
                    )
                    line_to_create = {
                        'name': payment.name,
                        'partner_id': payment.partner_id.id,
                        'account_id': partner_account.id,
                        'currency_id': payment.currency_id.id,
                        'amount_currency': amount,
                        'balance': payment.currency_id._convert(from_amount=amount, to_currency=self.env.company.currency_id),
                        'payment_lines_ids': [Command.set(payment.ids)],
                    }
                lines_to_create.append(line_to_create)
        return lines_to_create

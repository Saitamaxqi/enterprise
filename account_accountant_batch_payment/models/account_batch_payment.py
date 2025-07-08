# -*- coding: utf-8 -*-

from odoo import Command, models, _


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def action_open_batch_payment(self):
        self.ensure_one()
        return {
            'name': _("Batch Payment"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('account_batch_payment.view_batch_payment_form').id,
            'res_model': self._name,
            'res_id': self.id,
            'context': {
                'create': False,
                'delete': False,
            },
            'target': 'current',
        }

    def _get_amls_from_batch_payments(self, domain):
        amls = self.env['account.move.line']
        amls_to_create = []
        payments_with_move = self.payment_ids.filtered(lambda payment: payment.move_id)

        for payment in payments_with_move:
            liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
            amls |= liquidity_lines.filtered_domain(domain)

        amls_to_create += [
            aml._get_aml_values(
                balance=-aml.balance,
                amount_currency=-aml.amount_currency,
                reconciled_lines_ids=[Command.set(aml.ids)]
            ) for aml in amls
        ]

        amls_to_create += (self.payment_ids - payments_with_move)._get_amls_for_payment_without_move()
        return amls, amls_to_create

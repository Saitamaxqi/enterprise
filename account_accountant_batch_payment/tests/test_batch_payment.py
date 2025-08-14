# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestBatchPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a bank journal
        cls.journal = cls.company_data['default_journal_bank']
        cls.batch_deposit_method = cls.env.ref('account_batch_payment.account_payment_method_batch_deposit')
        cls.batch_deposit = cls.journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'batch_payment')
        cls.other_currency = cls.setup_other_currency('EUR')

    @classmethod
    def create_payment(cls, partner, amount, **kwargs):
        """ Create a batch deposit payment """
        payment = cls.env['account.payment'].create({
            'journal_id': cls.journal.id,
            'payment_type': 'inbound',
            'date': time.strftime('%Y') + '-07-15',
            'amount': amount,
            'partner_id': partner.id,
            'partner_type': 'customer',
            **kwargs,
        })
        payment.action_post()
        return payment

    @classmethod
    def _create_st_line(cls, amount=1000.0, date='2019-01-01', payment_ref='turlututu', **kwargs):
        return cls.env['account.bank.statement.line'].create({
            'journal_id': cls.journal.id,
            'amount': amount,
            'date': date,
            'payment_ref': payment_ref,
            'partner_id': cls.partner_a.id,
            **kwargs,
        })

    def test_zero_amount_payment(self):
        zero_payment = self.create_payment(self.partner_a, 0, payment_method_line_id=self.batch_deposit.id)
        batch_vals = {
            'journal_id': self.journal.id,
            'payment_ids': [(4, zero_payment.id, None)],
            'payment_method_id': self.batch_deposit_method.id,
        }
        self.assertRaises(ValidationError, self.env['account.batch.payment'].create, batch_vals)

    def test_exchange_diff_batch_payment(self):
        """
            This test will do a basic case where the company is in US Dollars but the st_line and the payment are in
            another currencies. Between the moment where we created the batch payment and the st_line a difference of
            rates happens and so an exchange diff is created.
        """
        self.other_currency = self.setup_other_currency('EUR', rates=[('2016-01-03', 2.0), ('2017-01-03', 1.0)])
        payment = self.create_payment(
            partner=self.partner_a,
            amount=100,
            date='2017-01-02',
            journal_id=self.company_data['default_journal_bank'].id,
            currency_id=self.other_currency.id,
        )
        payment.create_batch_payment()

        st_line = self._create_st_line(
            100.0,
            date='2017-01-05',
        )
        st_line.set_batch_payment_bank_statement_line(payment.batch_payment_id.id)
        self.assertRecordValues(st_line.line_ids, [
            {
                'account_id': st_line.journal_id.default_account_id.id,
                'amount_currency': 100.0,
                'currency_id': self.company_data['currency'].id,
                'balance': 100.0,
                'reconciled': False,
            },
            {
                'account_id': payment.outstanding_account_id.id,
                'amount_currency': -100.0,
                'currency_id': self.other_currency.id,
                'balance': -100.0,
                'reconciled': True,
            },
        ])
        exchange_move = st_line.line_ids[1].matched_debit_ids.exchange_move_id
        self.assertRecordValues(exchange_move.line_ids, [
            {
                'account_id': payment.outstanding_account_id.id,
                'currency_id': self.other_currency.id,
                'balance': 50.0,
            },
            {
                'account_id': self.env.company.income_currency_exchange_account_id.id,
                'currency_id': self.other_currency.id,
                'balance': -50.0,
            },
        ])

    def test_partner_account_batch_payments_without_journal_entry(self):
        """ Test that account receivable is used for inbound payments and account payable for outbound ones
            when no journal entry is linked to the payment
        """
        if self.env['account.move']._get_invoice_in_payment_state() == 'paid':
            self.skipTest("`accountant` module is not installed. A journal entry will always be linked to the payment.")
        for payment_type, account_a, account_b in [
            ('inbound', self.partner_a.property_account_receivable_id, self.partner_b.property_account_receivable_id),
            ('outbound', self.partner_a.property_account_payable_id, self.partner_b.property_account_payable_id),
        ]:
            payment_1 = self.env['account.payment'].create({
                'date': '2015-01-01',
                'payment_type': payment_type,
                'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
                'partner_id': self.partner_a.id,
                'payment_method_line_id': self.batch_deposit.id,
                'amount': 100.0,
            })
            payment_2 = self.env['account.payment'].create({
                'date': '2015-01-01',
                'payment_type': payment_type,
                'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
                'partner_id': self.partner_b.id,
                'payment_method_line_id': self.batch_deposit.id,
                'amount': 200.0,
            })
            payments = payment_1 + payment_2
            payments.action_post()
            batch = self.env['account.batch.payment'].create({
                'batch_type': payment_type,
                'journal_id': self.journal.id,
                'payment_ids': [Command.set(payments.ids)],
                'payment_method_id': self.batch_deposit_method.id,
            })
            batch.validate_batch()
            st_line_amount = 300.0 if payment_type == 'inbound' else -300.0
            st_line = self.env['account.bank.statement.line'].create({
                'journal_id': self.journal.id,
                'amount': st_line_amount,
                'date': '2015-01-01',
                'payment_ref': batch.name,
            })
            st_line.set_batch_payment_bank_statement_line(batch.id)
            bank_account = self.journal.default_account_id
            if payment_type == 'inbound':
                self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                    {'account_id': account_b.id, 'partner_id': self.partner_b.id, 'balance': -200.0},
                    {'account_id': account_a.id, 'partner_id': self.partner_a.id, 'balance': -100.0},
                    {'account_id': bank_account.id, 'partner_id': False, 'balance': 300.0},
                ])
            else:
                self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                    {'account_id': bank_account.id, 'partner_id': False, 'balance': -300.0},
                    {'account_id': account_a.id, 'partner_id': self.partner_a.id, 'balance': 100.0},
                    {'account_id': account_b.id, 'partner_id': self.partner_b.id, 'balance': 200.0},
                ])

    def test_partner_account_batch_payments_with_journal_entry(self):
        """ Test the account for batch payments with a linked journal entry """
        for payment_type, account_a, account_b in [
            ('inbound', self.partner_a.property_account_receivable_id, self.partner_b.property_account_receivable_id),
            ('outbound', self.partner_a.property_account_payable_id, self.partner_b.property_account_payable_id),
        ]:
            outstanding_account = self.env['account.payment']._get_outstanding_account(payment_type)
            self.batch_deposit.payment_account_id = outstanding_account
            payment_1 = self.env['account.payment'].create({
                'date': '2015-01-01',
                'payment_type': payment_type,
                'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
                'partner_id': self.partner_a.id,
                'payment_method_line_id': self.batch_deposit.id,
                'amount': 100.0,
            })
            payment_2 = self.env['account.payment'].create({
                'date': '2015-01-01',
                'payment_type': payment_type,
                'partner_type': 'customer' if payment_type == 'inbound' else 'supplier',
                'partner_id': self.partner_b.id,
                'payment_method_line_id': self.batch_deposit.id,
                'amount': 200.0,
            })
            payments = payment_1 + payment_2
            payments.action_post()
            batch = self.env['account.batch.payment'].create({
                'batch_type': payment_type,
                'journal_id': self.journal.id,
                'payment_ids': [Command.set(payments.ids)],
                'payment_method_id': self.batch_deposit_method.id,
            })
            batch.validate_batch()
            st_line_amount = 300.0 if payment_type == 'inbound' else -300.0
            st_line = self.env['account.bank.statement.line'].create({
                'journal_id': self.journal.id,
                'amount': st_line_amount,
                'date': '2015-01-01',
                'payment_ref': batch.name,
            })
            st_line.set_batch_payment_bank_statement_line(batch.id)
            bank_account = self.journal.default_account_id
            if payment_type == 'inbound':
                self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
                    {'account_id': account_b.id, 'partner_id': self.partner_b.id, 'balance': -200.0},
                    {'account_id': account_a.id, 'partner_id': self.partner_a.id, 'balance': -100.0},
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_a.id, 'balance': 100.0},
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_b.id, 'balance': 200.0},
                ])
                self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_b.id, 'balance': -200.0},
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_a.id, 'balance': -100.0},
                    {'account_id': bank_account.id, 'partner_id': False, 'balance': 300.0},
                ])
            else:
                self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_b.id, 'balance': -200.0},
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_a.id, 'balance': -100.0},
                    {'account_id': account_a.id, 'partner_id': self.partner_a.id, 'balance': 100.0},
                    {'account_id': account_b.id, 'partner_id': self.partner_b.id, 'balance': 200.0},
                ])
                self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                    {'account_id': bank_account.id, 'partner_id': False, 'balance': -300.0},
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_a.id, 'balance': 100.0},
                    {'account_id': outstanding_account.id, 'partner_id': self.partner_b.id, 'balance': 200.0},
                ])

# -*- coding: utf-8 -*-
from freezegun import freeze_time
from contextlib import closing

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestReconciliationMatchingRules(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        #################
        # Company setup #
        #################
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.other_currency_2 = cls.setup_other_currency('CAD', rates=[('2016-01-01', 10.0), ('2017-01-01', 20.0)])

        cls.account_rec = cls.company_data['default_account_receivable']
        cls.account_pay = cls.company_data['default_account_payable']
        cls.current_assets_account = cls.env['account.account'].search([
            ('account_type', '=', 'asset_current'),
            ('company_ids', '=', cls.company.id)], limit=1)

        cls.bank_journal = cls.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', cls.company.id)], limit=1)
        cls.cash_journal = cls.env['account.journal'].create({'type': 'cash', 'name': 'Cash'})

        cls.tax_account = cls.env['account.account'].create({
            'name': 'TAX_ACC',
            'code': 'TACC',
            'account_type': 'liability_current',
            'reconcile': False,
        })

        cls.tax21 = cls.env['account.tax'].create({
            'name': '21%',
            'type_tax_use': 'purchase',
            'amount': 21,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': cls.tax_account.id,
                }),
            ],
        })

        cls.partner_1 = cls.env['res.partner'].create({'name': 'partner_1', 'company_id': cls.company.id})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'partner_2', 'company_id': cls.company.id})
        cls.partner_3 = cls.env['res.partner'].create({'name': 'partner_3', 'company_id': cls.company.id})
        cls.partner_agrolait = cls.env['res.partner'].create({'name': 'Agrolait', 'company_id': cls.company.id})

        ###############
        # Rules setup #
        ###############
        cls.rule_1 = cls.env['account.reconcile.model'].create({
            'name': 'button that shouldn\'t be proposed',
            'sequence': 1,
            'match_partner_ids': [],
            'line_ids': [Command.create({'account_id': cls.current_assets_account.id})],
        })
        cls.rule_2 = cls.env['account.reconcile.model'].create({
            'name': 'button to be completed by each test',
            'sequence': 2,
            'match_journal_ids': [(6, 0, [cls.bank_journal.id])],
            'match_label': 'contains',
            'match_label_param': 'fees',
            'line_ids': [Command.create({'account_id': cls.current_assets_account.id})],
        })
        cls.mapping_partner_rule = cls.env['account.reconcile.model'].create({
            'name': 'mapping agrolait',
            'sequence': 100,
            'match_label': 'contains',
            'match_label_param': 'agrolait',
            'line_ids': [Command.create({'partner_id': cls.partner_agrolait.id})],
        })

    @classmethod
    def _create_invoice_line(cls, amount, partner, move_type, currency=None, ref=None, name=None, inv_date='2019-09-01'):
        ''' Create an invoice on the fly.'''
        invoice_form = Form(cls.env['account.move'].with_context(default_move_type=move_type, default_invoice_date=inv_date, default_date=inv_date))
        invoice_form.partner_id = partner
        if currency:
            invoice_form.currency_id = currency
        if ref:
            invoice_form.ref = ref
        if name:
            invoice_form.name = name
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'xxxx'
            invoice_line_form.quantity = 1
            invoice_line_form.price_unit = amount
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()
        invoice.action_post()
        lines = invoice.line_ids
        return lines.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))

    @classmethod
    def _create_st_line(cls, amount=1000.0, date='2019-01-01', payment_ref='turlututu', **kwargs):
        st_line = cls.env['account.bank.statement.line'].create({
            'journal_id': kwargs.get('journal_id', cls.bank_journal.id),
            'amount': amount,
            'date': date,
            'payment_ref': payment_ref,
            'partner_id': cls.partner_a.id,
            **kwargs,
        })
        return st_line

    @classmethod
    def _create_reconcile_model(cls, **kwargs):
        return cls.env['account.reconcile.model'].create({
            'name': "test",
            **kwargs,
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'amount_type': 'percentage',
                    'label': f"test {i}",
                    **line_vals,
                })
                for i, line_vals in enumerate(kwargs.get('line_ids', []))
            ],
        })

    @freeze_time('2020-01-01')
    def _check_st_line_matching(self, st_line, expected_values, reconciled_amls=None):
        reconciled_amls = reconciled_amls or []
        self.assertRecordValues(st_line.move_id.line_ids, expected_values)
        if not reconciled_amls:
            return
        for inv_line, rec_aml in zip(st_line.move_id.line_ids.filtered(lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable')), reconciled_amls):
            if inv_line.debit:
                self.assertEqual(inv_line.matched_credit_ids.credit_move_id, rec_aml)
            else:
                self.assertEqual(inv_line.matched_debit_ids.debit_move_id, rec_aml)

    def test_matching_buttons(self):
        bank_line_1, bank_line_2, cash_line_1 = self.env['account.bank.statement.line'].with_context(auto_statement_processing=True).create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'invoice 2020-01-01',
                'amount': 100,
                'sequence': 1,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'xxxxxfeesxxx',
                'partner_id': self.partner_1.id,
                'amount': 30,
                'sequence': 2,
            },
            {
                'journal_id': self.cash_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'yyyyyfees',
                'amount': -1000,
                'sequence': 1,
            },
        ])
        # no need to call the cron since we passed the contextual key to process the lines automatically
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False},
            {'account_id': self.bank_journal.suspense_account_id.id, 'reconcile_model_id': False},
        ], reconciled_amls=False)
        self._check_st_line_matching(bank_line_2, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False},
            {'account_id': self.bank_journal.suspense_account_id.id, 'reconcile_model_id': self.rule_2.id},
        ], reconciled_amls=False)
        self._check_st_line_matching(cash_line_1, [
            {'account_id': self.cash_journal.default_account_id.id, 'reconcile_model_id': False},
            {'account_id': self.cash_journal.suspense_account_id.id, 'reconcile_model_id': False},
        ], reconciled_amls=False)

    def test_button_with_taxes(self):
        bank_line_1 = self.env['account.bank.statement.line'].create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'xxxagrolaitxxfeesxxx',
                'amount': -121,
                'sequence': 1,
            },
        ])
        rule_tax = self.env['account.reconcile.model'].create({
            'name': 'button that includes some taxes on the lines to create',
            'sequence': 1,
            'match_partner_ids': [],
            'line_ids': [Command.create({'account_id': self.current_assets_account.id, 'tax_ids': self.tax21.ids})],
        })
        # push the button
        rule_tax._trigger_reconciliation_model(bank_line_1)
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False, 'partner_id': False, 'balance': -121.0},
            {'account_id': self.current_assets_account.id, 'reconcile_model_id': rule_tax.id, 'partner_id': False, 'balance': 100},
            {'account_id': self.tax_account.id, 'reconcile_model_id': False, 'partner_id': False, 'balance': 21},
        ], reconciled_amls=False)

    def test_partner_mapping(self):
        bank_line_1 = self.env['account.bank.statement.line'].with_context(auto_statement_processing=True).create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'xxxagrolaitxxfeesxxx',
                'amount': 30,
                'sequence': 2,
            },
        ])
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False, 'partner_id': self.partner_agrolait.id},
            {'account_id': self.bank_journal.suspense_account_id.id, 'reconcile_model_id': self.rule_2.id, 'partner_id': self.partner_agrolait.id},
        ], reconciled_amls=False)

    def test_matching_algorithm(self):
        invoice_line_1 = self._create_invoice_line(100, self.partner_1, 'out_invoice')
        invoice_line_2 = self._create_invoice_line(200, self.partner_1, 'out_invoice')
        invoice_line_3 = self._create_invoice_line(300, self.partner_1, 'in_refund', name="RBILL/2019/09/0013")
        invoice_line_4 = self._create_invoice_line(1000, self.partner_2, 'in_invoice')
        _invoice_line_5 = self._create_invoice_line(1000, self.partner_2, 'in_invoice')
        _invoice_line_6 = self._create_invoice_line(1000, self.partner_2, 'in_invoice')
        invoice_line_7 = self._create_invoice_line(100, self.partner_3, 'out_invoice')
        invoice_line_8 = self._create_invoice_line(600, self.partner_3, 'out_invoice', ref="RF12 3456")
        _invoice_line_9 = self._create_invoice_line(200, self.partner_3, 'out_invoice')
        invoice_line_10 = self._create_invoice_line(200, self.partner_agrolait, 'out_invoice')
        invoice_line_11 = self._create_invoice_line(12345.67, self.partner_2, 'out_invoice')

        bank_line_1, bank_line_2,\
        bank_line_3, bank_line_4,\
        bank_line_5, bank_line_6 = self.env['account.bank.statement.line'].create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'all open invoices',
                'partner_id': self.partner_1.id,
                'amount': 600,
                'sequence': 1,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': invoice_line_4.move_id.name,
                'partner_id': self.partner_2.id,
                'amount': -1600,
                'sequence': 2,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'approx due amount',
                'narration': 'Communication: RF12 3456',
                'partner_id': self.partner_3.id,
                'amount': 97,
                'sequence': 3,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'RF12 3456',
                'partner_id': self.partner_3.id,
                'amount': 100,
                'sequence': 4,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'transaction_details': {'no partner?': 'yes: agrolait'},
                'ref': 'RF12 3456',
                'amount': 200,
                'sequence': 5,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'yyyyy 12345.67 EUR fdfkmlk',
                'partner_id': self.partner_2.id,
                'amount': 12344.78,
                'sequence': 6,
            },
        ])
        self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines()
        # the total residual of the partner matches the line amount
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 600.0},
            {'account_id': self.account_rec.id, 'balance': -100.0},
            {'account_id': self.account_rec.id, 'balance': -200.0},
            {'account_id': self.account_pay.id, 'balance': -300.0},
        ], reconciled_amls=[invoice_line_1, invoice_line_2, invoice_line_3])

        # amount isn't the same, but partner and ref are
        self._check_st_line_matching(bank_line_2, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': -1600.0},
            {'account_id': self.account_pay.id, 'balance': 1000.0},
            {'account_id': self.bank_journal.suspense_account_id.id, 'balance': 600.0},  # always the suspense account because it's our way to know the reconciliation isn't over
        ], reconciled_amls=[invoice_line_4, False])

        # partner and amount almost equals the invoice (3% diff allowed)
        # TODO: partial reconciliation ok? -> NO fp asked for full so +97 - 100 + 3 (suspense account)
        self._check_st_line_matching(bank_line_3, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 97.0},
            {'account_id': self.account_rec.id, 'balance': -97.0},
        ], reconciled_amls=[invoice_line_7])

        # amount isn't the same, but partner and ref are
        self._check_st_line_matching(bank_line_4, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 100.0},
            {'account_id': self.account_rec.id, 'balance': -100.0},
        ], reconciled_amls=[invoice_line_8])

        # mapping of agrolait first, then because we have the partner the correct invoice can be found
        self._check_st_line_matching(bank_line_5, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 200.0, 'partner_id': self.partner_agrolait.id},
            {'account_id': self.account_rec.id, 'balance': -200.0, 'partner_id': self.partner_agrolait.id},
        ], reconciled_amls=[invoice_line_10])

        # invoice amount found in the payment ref and partner identified
        self._check_st_line_matching(bank_line_6, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 12344.78, 'partner_id': self.partner_2.id},
            {'account_id': self.account_rec.id, 'balance': -12344.78, 'partner_id': self.partner_2.id},
        ], reconciled_amls=[invoice_line_11])

    def test_auto_rule_creation_and_matching(self):
        account_a = self.env['account.account'].create({
            'name': "Custom Account A",
            'code': "010101",
            'account_type': "asset_current",
        })
        account_b = self.env['account.account'].create({
            'name': "Custom Account B",
            'code': "020202",
            'account_type': "asset_current",
        })
        bank_stmt_line_1 = self._create_st_line(amount=1000, payment_ref='VISA PAYMENT RENT ON 2020-01-01 FOR JAN')
        bank_stmt_line_2 = self._create_st_line(amount=1000, payment_ref='VISA PAYMENT RENT ON 2020-02-01 FOR FEB')

        bank_stmt_line_1.set_account_bank_statement_line(bank_stmt_line_1.line_ids[-1].id, account_a.id)
        bank_stmt_line_2.set_account_bank_statement_line(bank_stmt_line_2.line_ids[-1].id, account_a.id)
        # Assert that the reconciliation model has been created with the correct parameters.
        reco_model = self.env['account.reconcile.model'].search([
            ('match_label', '=', 'match_regex'),
            ('match_label_param', '=', 'VISA PAYMENT RENT ON \\d+-\\d+-\\d+ FOR'),
            ('match_partner_ids', '=', self.partner_a.ids),
            ('match_amount', '=', 'between'),
            ('match_amount_min', '=', 1000 - 0.01),
            ('match_amount_max', '=', 1000 + 0.01),
            ('line_ids.account_id', '=', account_a.id),
        ])
        self.assertTrue(reco_model.exists())

        bank_stmt_line_3 = self._create_st_line(amount=1000, payment_ref='VISA PAYMENT RENT ON 2020-03-01 FOR MAR')
        bank_stmt_line_3._try_auto_reconcile_statement_lines()
        # Assert that the created model will be used as a suggestion.
        self.assertEqual(bank_stmt_line_3.line_ids[-1].reconcile_model_id.id, reco_model.id)

        # Assert that the rule is deleted when another account is selected while having a suggestion.
        bank_stmt_line_3.set_account_bank_statement_line(bank_stmt_line_3.line_ids[-1].id, account_b.id)
        self.assertFalse(reco_model.exists())

    def test_auto_rule_creation_and_matching_with_structured_reference(self):
        account_a = self.env['account.account'].create({
            'name': "Custom Account A",
            'code': "010101",
            'account_type': "asset_current",
        })
        bank_stmt_line_1 = self._create_st_line(amount=100, payment_ref='TAX +++123/12345/1234+++ 100 EUR')
        bank_stmt_line_2 = self._create_st_line(amount=200, payment_ref='TAX +++123/12345/1234+++ 200 EUR')

        bank_stmt_line_1.set_account_bank_statement_line(bank_stmt_line_1.line_ids[-1].id, account_a.id)
        bank_stmt_line_2.set_account_bank_statement_line(bank_stmt_line_2.line_ids[-1].id, account_a.id)
        # Assert that the reconciliation model and that the structured reference has been perserved.
        reco_model = self.env['account.reconcile.model'].search([
            ('match_label', '=', 'match_regex'),
            ('match_label_param', '=', 'TAX \\+\\+\\+123/12345/1234\\+\\+\\+ \\d+ EUR'),
        ])
        self.assertTrue(reco_model.exists())

        bank_stmt_line_3 = self._create_st_line(amount=300, payment_ref='TAX +++123/12345/1234+++ 300 EUR')
        bank_stmt_line_3._try_auto_reconcile_statement_lines()
        # Assert that the created model will be used as a suggestion.
        self.assertEqual(bank_stmt_line_3.line_ids[-1].reconcile_model_id.id, reco_model.id)

    def test_discount_amount(self):
        _invoice_line_1 = self._create_invoice_line(100, self.partner_1, 'out_invoice')
        invoice_line_2 = self._create_invoice_line(100, self.partner_1, 'out_invoice')
        bank_line_1 = self.env['account.bank.statement.line'].with_context(auto_statement_processing=True).create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-02-01',
                'payment_ref': 'no clear identification of the paid invoice',
                'partner_id': self.partner_1.id,
                'amount': 95,
                'sequence': 1,
            }
        ])

        bank_line_1._try_auto_reconcile_statement_lines()
        # no proposal, since there are several possibilities
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 95.0},
            {'account_id': self.bank_journal.suspense_account_id.id, 'balance': -95.0},
        ], reconciled_amls=[])

        # add early payment discount info
        invoice_line_2.discount_date = '2020-01-15'
        invoice_line_2.discount_balance = 95.0

        bank_line_1._try_auto_reconcile_statement_lines()
        # early payment not matching because payment date is after the discount date
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 95.0},
            {'account_id': self.bank_journal.suspense_account_id.id, 'balance': -95.0},
        ], reconciled_amls=[])

        # add early payment discount info
        bank_line_1.date = '2020-01-14'
        bank_line_1._try_auto_reconcile_statement_lines()
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 95.0},
            {'account_id': self.account_rec.id, 'balance': -95.0},
        ], reconciled_amls=[invoice_line_2])

    def test_no_partner_ambiguity(self):
        _invoice_line_1 = self._create_invoice_line(600, self.partner_1, 'out_invoice', ref="RF12 3456")
        _invoice_line_2 = self._create_invoice_line(600, self.partner_2, 'out_invoice', ref="RF12 3456")
        bank_line = self.env['account.bank.statement.line'].with_context(auto_statement_processing=True).create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'RF12 3456',
                'amount': 600,
                'sequence': 1,
            },
        ])
        # no proposal, since there are several possibilities
        self._check_st_line_matching(bank_line, [
            {'account_id': self.bank_journal.default_account_id.id, 'balance': 600.0},
            {'account_id': self.bank_journal.suspense_account_id.id, 'balance': -600.0},
        ], reconciled_amls=[])

    def test_widget_available_for_line(self):
        """
            Tests what the reconcileModelPerStatementLineId (js side) will receive
            A reco model is valid for a statement line if the value to filter is valid on the statement line or if
            it is not specified on the model
            Used to know which reconcile model to show in the list on the statement line
        """
        self.env['account.reconcile.model'].search([]).unlink()  # Don't want it to appear in suggestion
        bank_line_1, bank_line_2, bank_line_3 = self.env['account.bank.statement.line'].create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'Line 1',
                'amount': -121,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'Line 2',
                'partner_id': self.partner_1.id,
                'amount': -121,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'xxxagrolaitxxfeesxxx',
                'partner_id': self.partner_1.id,
                'amount': 500,
            },
        ])

        model_everywhere = self.env['account.reconcile.model'].create(
            {
                'name': "Shown everywhere",
                'line_ids': [
                    Command.create({'account_id': self.current_assets_account.id}),
                    Command.create({'account_id': self.account_pay.id}),
                ],
            },
        )
        self.env['account.reconcile.model'].create(
            {
                'name': "Never shown because no Counterpart wit account",
                'line_ids': [Command.create({'partner_id': self.partner_1.id})],
            },
        )
        model_partner_a = self.env['account.reconcile.model'].create(
            {
                'name': "Needs partner 1",
                'match_partner_ids': self.partner_1.ids,
                'line_ids': [Command.create({'account_id': self.current_assets_account.id})],
            },
        )
        model_amount = self.env['account.reconcile.model'].create(
            {
                'name': "Needs amount",
                'match_amount': 'greater',
                'match_amount_min': 200,
                'line_ids': [Command.create({'account_id': self.current_assets_account.id})],
            },
        )
        model_partner_a_amount = self.env['account.reconcile.model'].create(
            {
                'name': "Needs amount and partner 1",
                'match_amount': 'greater',
                'match_amount_min': 200,
                'match_partner_ids': self.partner_1.ids,
                'line_ids': [Command.create({'account_id': self.current_assets_account.id})],
            },
        )
        model_label = self.env['account.reconcile.model'].create(
            {
                'name': "Needs label",
                'match_label': 'contains',
                'match_label_param': 'fees',
                'line_ids': [Command.create({'account_id': self.current_assets_account.id})],
            },
        )

        models_per_line = self.env['account.reconcile.model'].with_context(lang='en_US').get_available_reconcile_model_per_statement_line(
            (bank_line_1 + bank_line_2 + bank_line_3).ids
        )
        self.assertEqual(
            models_per_line[bank_line_1.id],
            [
                {'id': model_everywhere.id, 'display_name': "Shown everywhere"},
            ],
            "Does not match the amounts or partners"
        )
        self.assertEqual(
            models_per_line[bank_line_2.id],
            [
                {'id': model_everywhere.id, 'display_name': "Shown everywhere"},
                {'id': model_partner_a.id, 'display_name': "Needs partner 1"},
            ],
            "Only match the partner"
        )
        self.assertEqual(
            models_per_line[bank_line_3.id],
            [
                {'id': model_everywhere.id, 'display_name': "Shown everywhere"},
                {'id': model_partner_a.id, 'display_name': "Needs partner 1"},
                {'id': model_amount.id, 'display_name': 'Needs amount'},
                {'id': model_partner_a_amount.id, 'display_name': 'Needs amount and partner 1'},
                {'id': model_label.id, 'display_name': 'Needs label'},
            ],
            "Match the partner, the amount and the label"
        )

    def test_modify_reco_model_apply_on_statement_line(self):
        """
        This test will check that modifying a reco model will change the suggestion on statement lines
        """
        bank_line_1, bank_line_2 = self.env['account.bank.statement.line'].with_context(auto_statement_processing=True).create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'fees',
                'amount': 100,
            },
            {
                'journal_id': self.bank_journal.id,
                'date': '2020-01-01',
                'payment_ref': 'blblbl',
                'amount': 100,
            },
        ])
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False},
            {'account_id': self.bank_journal.suspense_account_id.id, 'reconcile_model_id': self.rule_2.id},
        ], reconciled_amls=False)

        self.rule_2.match_label_param = 'blblbl'
        self._check_st_line_matching(bank_line_1, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False},
            {'account_id': self.bank_journal.suspense_account_id.id, 'reconcile_model_id': False},
        ], reconciled_amls=False)
        self._check_st_line_matching(bank_line_2, [
            {'account_id': self.bank_journal.default_account_id.id, 'reconcile_model_id': False},
            {'account_id': self.bank_journal.suspense_account_id.id, 'reconcile_model_id': self.rule_2.id},
        ], reconciled_amls=False)

    # TODO add tests on multi companies
    # TODO add tests on multi currencies
    # TODO add tests on taxes
    # TODO add tests on proposed buttons / applicability (conditions of appearance)
    # TODO add tests on auto_reconcile trigger

#    def test_no_amount_check_keep_first(self):
#        """ In case the reconciliation model doesn't check the total amount of the candidates,
#        we still don't want to suggest more than are necessary to match the statement.
#        For example, if a statement line amounts to 250 and is to be matched with three invoices
#        of 100, 200 and 300 (retrieved in this order), only 100 and 200 should be proposed.
#        """
#        self.bank_line_2.amount = 250
#        self.bank_line_1.partner_id = None
#
#        self._check_statement_matching(self.rule_1, {
#            self.bank_line_1: {},
#            self.bank_line_2: {
#                'amls': self.invoice_line_1 + self.invoice_line_2,
#                'model': self.rule_1,
#                'status': 'write_off',
#            },
#        })
#
#    def test_no_amount_check_exact_match(self):
#        """ If a reconciliation model finds enough candidates for a full reconciliation,
#        it should still check the following candidates, in case one of them exactly
#        matches the amount of the statement line. If such a candidate exist, all the
#        other ones are disregarded.
#        """
#        self.bank_line_2.amount = 300
#        self.bank_line_1.partner_id = None
#
#        self._check_statement_matching(self.rule_1, {
#            self.bank_line_1: {},
#            self.bank_line_2: {
#                'amls': self.invoice_line_3,
#                'model': self.rule_1,
#                'status': 'write_off',
#            },
#        })
#

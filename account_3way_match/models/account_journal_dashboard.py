# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.osv import expression
from odoo.tools import SQL


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def open_action(self):
        action = super(AccountJournal, self).open_action()
        view = self.env.ref('account.action_move_in_invoice_type')
        if view and action.get("id") == view.id:
            action['context']['search_default_in_invoice'] = 0
            account_purchase_filter = self.env.ref('account_3way_match.account_invoice_filter_inherit_account_3way_match', False)
            action['search_view_id'] = account_purchase_filter and [account_purchase_filter.id, account_purchase_filter.name] or False
        return action

    def _get_open_sale_purchase_query(self, journal_type):
        # OVERRIDE
        assert journal_type in ('sale', 'purchase')
        query = self.env['account.move.line']._where_calc([
            ('move_id', 'in', self.env['account.move']._where_calc([
                *self.env['account.move.line']._check_company_domain(self.env.companies),
                ('journal_id', 'in', self.ids),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('move_type', '=', 'out_invoice') if journal_type == 'sale' else ('move_type', 'in', ('in_invoice', 'in_refund')),
                ('state', '=', 'posted'),
            ])),
            ('account_type', '=', 'asset_receivable' if journal_type == 'sale' else 'liability_payable'),
        ])

        account_move_alias = query.join(lhs_alias='account_move_line', lhs_column='move_id', rhs_table='account_move', rhs_column='id', link='move_id')

        selects = [
            SQL("account_move_line.journal_id"),
            SQL("account_move_line.company_id"),
            SQL("account_move_line.currency_id AS currency"),
            SQL("account_move_line.date_maturity < %s AS late", fields.Date.context_today(self)),
            SQL("SUM(%s) AS amount_total_company", SQL.identifier(account_move_alias, 'amount_total_signed')),
            SQL("SUM(%s) AS amount_total", SQL.identifier(account_move_alias, 'amount_total_signed')),
            SQL("COUNT(*)"),
            SQL("%s IN ('yes', 'exception') AS to_pay", SQL.identifier(account_move_alias, 'release_to_pay')),
        ]

        return query, selects

    def _get_draft_sales_purchases_query(self):
        # OVERRIDE
        domain_sale = [
            ('journal_id', 'in', self.filtered(lambda j: j.type == 'sale').ids),
            ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True))
        ]

        domain_purchase = [
            ('journal_id', 'in', self.filtered(lambda j: j.type == 'purchase').ids),
            ('move_type', 'in', self.env['account.move'].get_purchase_types(include_receipts=False)),
            '|',
            ('invoice_date_due', '<', fields.Date.today()),
            ('release_to_pay', '=', 'yes')
        ]
        domain = expression.AND([
            [('state', '=', 'draft'), ('payment_state', 'in', ('not_paid', 'partial'))],
            expression.OR([domain_sale, domain_purchase])
        ])
        return self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            *domain
        ])

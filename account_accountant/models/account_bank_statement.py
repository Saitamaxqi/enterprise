import logging
import re
import string

from markupsafe import Markup
from dateutil.relativedelta import relativedelta
from itertools import product

from odoo import Command, _, api, fields, models, SUPERUSER_ID
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.addons.base.models.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)


class AccountBankStatement(models.Model):
    _name = 'account.bank.statement'
    _inherit = ['mail.thread.main.attachment', 'account.bank.statement']

    def action_open_bank_reconcile_widget(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            name=self.name,
            default_context={
                'search_default_statement_id': self.id,
                'search_default_journal_id': self.journal_id.id,
            },
            extra_domain=[('statement_id', '=', self.id)]
        )

    def action_generate_attachment(self):
        ir_actions_report_sudo = self.env['ir.actions.report'].sudo()
        statement_report_action = self.env.ref('account.action_report_account_statement')
        for statement in self:
            statement_report = statement_report_action.sudo()
            content, _content_type = ir_actions_report_sudo._render_qweb_pdf(statement_report, res_ids=statement.ids)
            statement.attachment_ids |= self.env['ir.attachment'].create({
                'name': _("Bank Statement %s.pdf", statement.name) if statement.name else _("Bank Statement.pdf"),
                'type': 'binary',
                'mimetype': 'application/pdf',
                'raw': content,
                'res_model': statement._name,
                'res_id': statement.id,
            })
        return statement_report_action.report_action(docids=self)


class AccountBankStatementLine(models.Model):
    _name = 'account.bank.statement.line'
    _inherit = ['account.bank.statement.line', 'mail.thread.main.attachment']

    # Technical field holding the date of the last time the cron tried to auto-reconcile the statement line. Used to
    # optimize the bank matching process"
    cron_last_check = fields.Datetime()

    bank_statement_attachment_ids = fields.One2many('ir.attachment', compute='_compute_bank_statement_attachment_ids')
    attachment_ids = fields.One2many('ir.attachment', related="move_id.attachment_ids")

    def action_save_close(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_save_new(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_bank_statement_line_form_bank_rec_widget')
        action['context'] = {'default_journal_id': self._context['default_journal_id']}
        return action

    ####################################################
    # COMPUTE METHODS
    ####################################################

    def _compute_bank_statement_attachment_ids(self):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.bank.statement'),
            ('res_id', 'in', self.statement_id.ids),
            ('res_field', 'in', (False, 'invoice_pdf_report_file')),
        ]).grouped('res_id')

        for st_line in self:
            st_line.bank_statement_attachment_ids = attachments.get(st_line.statement_id.id)

    ####################################################
    # RECONCILIATION PROCESS
    ####################################################

    @api.model
    def _action_open_bank_reconciliation_widget(self, extra_domain=None, default_context=None, name=None, kanban_first=True):
        if default_context is None:
            default_context = {}
        action_reference = 'account_accountant.action_bank_statement_line_transactions' + ('_kanban' if kanban_first else '')
        action = self.env['ir.actions.act_window']._for_xml_id(action_reference)

        default_journal = self.env['account.journal'].browse(
            default_context.get('default_journal_id', default_context.get('search_default_journal_id'))
        )

        action.update({
            'name': name or _("Bank Matching"),
            'context': {**default_context, 'bank_statements_source': default_journal.exists().bank_statements_source},
            'domain': (extra_domain or []),
        })

        return action

    def action_open_recon_st_line(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            name=self.name,
            default_context={
                'default_statement_id': self.statement_id.id,
                'default_journal_id': self.journal_id.id,
                'default_st_line_id': self.id,
                'search_default_id': self.id,
            },
        )

    def _cron_try_auto_reconcile_statement_lines(self, batch_size=None, limit_time=0, company_id=None):
        """ Method called by the CRON to reconcile the statement lines automatically.

        :param batch_size: The maximum number of statement lines that could be processed at once by the CRON to avoid
                           a timeout. If specified, the CRON will be trigger again asap using a CRON trigger in case
                           there are still some statement lines to process.
        :param limit_time: Maximum time allowed to run in seconds. 0 if the Cron is allowed to run without time limit.
        :param company_id: Limits the processing to statement lines related to a single company.
        """
        def compute_st_lines_to_reconcile(company_id=None):
            # Find the bank statement lines that are not reconciled and try to reconcile them automatically.
            # The ones that are never be processed by the CRON before are processed first.
            remaining_line_id = None
            limit = batch_size + 1 if batch_size else None
            domain = Domain([
                ('is_reconciled', '=', False),
                ('cron_last_check', '=', False),
            ])
            if company_id is not None:
                domain &= Domain(self.env['account.reconcile.model']._check_company_domain(company_id))
            st_lines = self.search(domain, limit=limit, order="cron_last_check ASC NULLS FIRST, id")
            if batch_size and len(st_lines) > batch_size:
                remaining_line_id = st_lines[batch_size].id
                st_lines = st_lines[:batch_size]
            return st_lines, remaining_line_id

        def stopping_condition():
            if batch_size and limit_time:
                # cron limitations only make sense if we have both a batch_size and a limit_time
                return fields.Datetime.now().timestamp() - start_time.timestamp() > limit_time
            # the cron won't be limited, and we'll process all the statement lines never processed before
            return True

        remaining_line_id = None

        start_time = fields.Datetime.now()
        while stopping_condition():
            # compute the statement lines to reconcile in this batch size
            st_lines, remaining_line_id = compute_st_lines_to_reconcile(company_id=company_id)

            if not st_lines:
                return

            st_lines._try_auto_reconcile_statement_lines(company_id=company_id)

        if remaining_line_id:
            # If some statement lines couldn't be processed because of the cron limits, manually re-trigger the cron
            self.env.ref('account_accountant.auto_reconcile_bank_statement_line')._trigger()

    def _try_auto_reconcile_statement_lines(self, company_id=None):
        # The field `cron_last_check` will be written on all processed lines that requires them to be protected against
        # concurrent update to avoid the whole transaction to be rolled back.
        self.lock_for_update()

        # get all the reco models to consider (partner mapping and buttons)
        domain = []
        if company_id is not None:
            domain = Domain(self.env['account.reconcile.model']._check_company_domain(company_id))
        reco_models = self.env['account.reconcile.model'].search(domain)

        # partner mapping
        self.env['account.reconcile.model'].flush_model()
        self.flush_recordset(['journal_id', 'transaction_details', 'payment_ref', 'company_id'])
        self._cr.execute(SQL("""
            WITH matching_journal_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(account_journal_id) AS ids
                      FROM account_journal_account_reconcile_model_rel
                  GROUP BY account_reconcile_model_id
                 )

          SELECT st_line.id AS st_line_id, reco_model.mapped_partner_id
            FROM account_bank_statement_line st_line
       LEFT JOIN LATERAL (
                   SELECT reco_model.id,
                          reco_model.mapped_partner_id
                     FROM account_reconcile_model reco_model
                LEFT JOIN matching_journal_ids ON reco_model.id = matching_journal_ids.account_reconcile_model_id
                    WHERE (matching_journal_ids.ids IS NULL OR st_line.journal_id = ANY(matching_journal_ids.ids))
                      AND reco_model.mapped_partner_id IS NOT NULL
                      AND (
                              (
                                  reco_model.match_label = 'contains'
                                  AND (
                                      st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                   )
                              ) OR (
                                  reco_model.match_label = 'not_contains'
                                  AND NOT (
                                      st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                  )
                              ) OR (
                                  reco_model.match_label = 'match_regex'
                                  AND (
                                      st_line.payment_ref ~ reco_model.match_label_param
                                      OR st_line.transaction_details::TEXT ~ reco_model.match_label_param
                                  )
                              )
                          )
                      AND reco_model.id IN %s
                      AND reco_model.company_id = st_line.company_id
                 ORDER BY reco_model.sequence ASC, reco_model.id ASC
                    LIMIT 1
                 ) AS reco_model ON TRUE
           WHERE st_line.id IN %s
             AND st_line.partner_id IS NULL
             AND reco_model.mapped_partner_id IS NOT NULL
            """, tuple(reco_models.ids), tuple(self.ids)))

        for st_line_id, mapped_partner_id in self._cr.fetchall():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)  # guarantees batch prefetching if needed
            st_line.partner_id = mapped_partner_id

        # global flushing of tables that should not be updated between the different SQL queries
        self.env['account.account'].flush_model(['account_type', 'active'])
        self.env['account.move'].flush_model(['date', 'amount_total'])

        # First try to match invoices and payments where we can't be wrong:
        # Either the total residual for the partner is equal to the statement line amount
        # Either the statement line is referencing an invoice
        self.env['account.move.line'].flush_model([
            'account_id', 'partner_id', 'company_id',
            'amount_residual', 'reconciled', 'ref', 'move_name',
        ])
        self.flush_recordset(['payment_ref', 'partner_id', 'company_id'])
        self._cr.execute(SQL("""
            SELECT st_line.id AS st_line_id,
                   ARRAY_AGG(aml.id ORDER BY aml.id ASC) AS all_aml_ids,
                   SUM(aml.amount_residual) AS total_residual,
                   ARRAY_AGG(aml.id ORDER BY aml.id ASC) FILTER (
                      WHERE (aml.ref = st_line.payment_ref OR aml.move_name = st_line.payment_ref OR move.payment_reference = st_line.payment_ref)
                   ) AS ref_aml_ids
              FROM account_bank_statement_line st_line, account_move_line aml
         LEFT JOIN account_move move ON aml.move_id = move.id
         LEFT JOIN account_account acc ON aml.account_id = acc.id
             WHERE aml.partner_id = st_line.partner_id
               AND st_line.partner_id IS NOT NULL
               AND aml.company_id = st_line.company_id
               AND aml.reconciled = false
               AND acc.account_type IN ('asset_receivable', 'liability_payable')
               AND acc.active
               AND st_line.id IN %s
          GROUP BY st_line.id
        """, tuple(self.ids)))

        # process then remove matched statement lines
        processed_st_line_ids = set()
        lines_to_assign_models_ids = set()
        for st_line_id, all_aml_ids, total_residual, ref_aml_ids in self._cr.fetchall():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)  # guarantees batch prefetching if needed
            if total_residual == st_line.amount:
                st_line.set_line_bank_statement_line(all_aml_ids)
            elif ref_aml_ids:
                st_line.set_line_bank_statement_line(ref_aml_ids)
            else:
                # no valid candidates yet
                continue
            processed_st_line_ids.add(st_line_id)
            if not st_line.currency_id.is_zero(st_line.amount_residual):
                lines_to_assign_models_ids.add(st_line_id)
        remaining_st_line_ids = list(set(self.ids) - processed_st_line_ids)
        remaining_st_lines = self.filtered(lambda x: x.id not in processed_st_line_ids)

        if lines_to_assign_models_ids:
            lines_to_assign_models = self.browse(lines_to_assign_models_ids).with_prefetch(self._prefetch_ids)
            reco_models._apply_reconcile_models(lines_to_assign_models)

        # early return if we already processed everything
        if not remaining_st_lines:
            self.write({'cron_last_check': fields.Datetime.now()})
            return

        # Then try to match invoices and payments with a small tolerance on the different criteria
        self.env['account.move.line'].flush_model([
            'ref', 'move_id', 'move_name', 'account_id', 'partner_id', 'company_id',
            'reconciled', 'company_currency_id', 'amount_residual',
            'currency_id', 'amount_residual_currency',
            'discount_date', 'discount_balance', 'discount_amount_currency',
        ])
        remaining_st_lines.flush_recordset([
            'move_id', 'partner_id', 'company_id', 'currency_id',
            'amount', 'foreign_currency_id', 'amount_currency', 'payment_ref'
        ])
        self._cr.execute(SQL('''
             -- Either the partner is set, and
             SELECT st_line.id AS st_line_id,
                    MIN(aml.id) AS aml_id
               FROM account_bank_statement_line st_line
          LEFT JOIN account_move st_line_move ON st_line.move_id = st_line_move.id,
                    account_move_line aml
          LEFT JOIN account_account acc ON aml.account_id = acc.id
          LEFT JOIN account_move move ON aml.move_id = move.id
              WHERE aml.partner_id = st_line.partner_id
                AND st_line.partner_id IS NOT NULL
                AND aml.company_id = st_line.company_id
                AND aml.reconciled = false
                AND acc.account_type IN ('asset_receivable', 'liability_payable')
                AND acc.active
                AND st_line.id IN %s
                -- we have only one invoice matching the exact amount, even if the payment reference doesn't match
                -- or the invoice discount amount is the same as the statement line amount and paid in the allowed time limit
                -- or there is a small difference, in the allowed error margin (3%%)
                -- or the invoice original amount can be found in the the statement line label (with . or ,)
                AND (
                        (
                            -- in company currency
                            st_line.currency_id = aml.company_currency_id
                            AND (
                               aml.amount_residual = st_line.amount
                               OR (aml.discount_balance = st_line.amount AND st_line_move.date <= aml.discount_date)
                               OR (st_line.amount BETWEEN aml.amount_residual * 97/100 AND aml.amount_residual * 103/100)
                            )
                        ) OR (
                            -- in secondary currency: statement currency is the same as the invoice
                            st_line.currency_id = aml.currency_id
                            AND (
                               aml.amount_residual_currency = st_line.amount
                               OR (aml.discount_amount_currency = st_line.amount AND st_line_move.date <= aml.discount_date)
                               OR (st_line.amount BETWEEN aml.amount_residual_currency * 97/100 AND aml.amount_residual_currency * 103/100)
                            )
                        ) OR (
                            -- in secondary currency: statement secondary currency is the same as the invoice
                            st_line.foreign_currency_id = aml.currency_id
                            AND (
                                aml.amount_residual_currency = st_line.amount_currency
                                OR (aml.discount_amount_currency = st_line.amount_currency AND st_line_move.date <= aml.discount_date)
                                OR (st_line.amount_currency BETWEEN aml.amount_residual_currency * 97/100 AND aml.amount_residual_currency * 103/100)
                            )
                        ) OR (
                            REPLACE(st_line.payment_ref, ',', '.') ILIKE '%%' || TRIM(trailing '0' FROM move.amount_total::TEXT) || '%%'
                        )
                )
           GROUP BY st_line.id
             HAVING COUNT(*) = 1

            UNION ALL

             -- Either the partner is not set, and
             SELECT st_line.id AS st_line_id,
                    MIN(aml.id) AS aml_id
               FROM account_bank_statement_line st_line, account_move_line aml
          LEFT JOIN account_account acc ON aml.account_id = acc.id
          LEFT JOIN account_move move ON aml.move_id = move.id
              WHERE st_line.partner_id IS NULL
                AND aml.company_id = st_line.company_id
                AND aml.reconciled = false
                AND acc.account_type IN ('asset_receivable', 'liability_payable')
                AND acc.active
                AND st_line.id IN %s
                AND st_line.currency_id = aml.currency_id
                AND (st_line.payment_ref = aml.move_name OR st_line.payment_ref = aml.ref OR st_line.payment_ref = move.payment_reference)
                -- we have only one invoice matching the reference and amount, or the amount found in the statement line label
                AND (
                     (aml.amount_residual BETWEEN st_line.amount AND st_line.amount * 103/100)
                     OR (
                         REPLACE(st_line.payment_ref, ',', '.') ILIKE '%%' || TRIM(trailing '0' FROM move.amount_total::TEXT) || '%%'
                     )
                )
           GROUP BY st_line.id
             HAVING COUNT(*) = 1
        ''', tuple(remaining_st_line_ids), tuple(remaining_st_line_ids)))

        # process then remove matched statement lines
        for st_line_id, aml_id in self._cr.fetchall():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)  # guarantees batch prefetching if needed
            st_line.set_line_bank_statement_line(aml_id)
            if st_line.currency_id.is_zero(st_line.amount_residual):
                processed_st_line_ids.add(st_line_id)
        remaining_st_line_ids = list(set(remaining_st_line_ids) - processed_st_line_ids)

        if remaining_st_line_ids:
            # try to apply reco models on the remaining statement lines
            remaining_st_lines = self.browse(remaining_st_line_ids).with_prefetch(self._prefetch_ids)
            reco_models._apply_reconcile_models(remaining_st_lines)

        self.write({'cron_last_check': fields.Datetime.now()})

    def _retrieve_partner(self):
        self.ensure_one()

        # partner already set on the statement line.
        if self.partner_id:
            return

        # Retrieve the partner from the bank account.
        if self.account_number:
            account_number_nums = sanitize_account_number(self.account_number)
            if account_number_nums:
                domain = [('sanitized_acc_number', 'ilike', account_number_nums)]
                for extra_domain in ([('company_id', 'parent_of', self.company_id.id)], [('company_id', '=', False)]):
                    bank_accounts = self.env['res.partner.bank'].search(extra_domain + domain)
                    if len(bank_accounts.partner_id) == 1:
                        return bank_accounts.partner_id
                    else:
                        # We have several partner with same account, possibly some archived partner
                        # so try to filter out inactive partner and if one remains, select this one
                        bank_accounts = bank_accounts.filtered(lambda bacc: bacc.partner_id.active)
                        if len(bank_accounts.partner_id) == 1:
                            return bank_accounts.partner_id

        # Retrieve the partner from the partner name.
        if self.partner_name:
            # using 'complete_name' instead of 'name',
            # as 'complete_name' is the first search criteria in _rec_names_search,
            # and trigram indexed accordingly.
            domains = product(
                [
                    ('complete_name', '=ilike', self.partner_name),
                    ('complete_name', 'ilike', self.partner_name),
                ],
                [
                    ('company_id', 'parent_of', self.company_id.id),
                    ('company_id', '=', False),
                ],
            )
            for domain in domains:
                partner = self.env['res.partner'].search(list(domain) + [('parent_id', '=', False)], limit=2)
                if len(partner) == 1:
                    return partner

            # Retrieve the partner from the last 3 statement lines with the same partner_name
            grouped_st_lines = self.search([
                *self._check_company_domain(self.company_id),
                ('partner_name', '=', self.partner_name), ('is_reconciled', '=', True)
            ], limit=3).grouped('partner_id')
            if len(grouped_st_lines) == 1:
                for partner_id in grouped_st_lines:
                    return partner_id

        return self.env['res.partner']

    def _action_manual_reco_model(self, reco_model_id):
        self.move_id.line_ids.filtered(lambda x: x.account_id == x.move_id.journal_id.suspense_account_id).reconcile_model_id = reco_model_id

    def _get_counterpart_aml(self, open_balance):
        """ Generates a counterpart account move line based on the given open balance.

            :param open_balance: The open balance amount that will be used to create the counterpart account move line.
            :returns: A dictionary containing the values to create a counterpart account move line, with
                     keys like "name", "account_id", "amount_currency", and "currency_id".
        """
        self.ensure_one()
        currency = self.foreign_currency_id or self.currency_id or self.journal_id.currency_id or self.env.company.currency_id
        return {
            'name': self.payment_ref,
            'account_id': self.journal_id.suspense_account_id.id,
            'balance': -open_balance,
            'currency_id': currency.id,
            'amount_currency': currency.round(-open_balance * currency.rate)
        }

    def _get_partner_id(self, lines_to_add_partner_ids):
        """ Determines the appropriate partner ID based on the set of partner IDs
            passed to it.

            :param lines_to_add_partner_ids: A set of partner IDs to evaluate.
            :returns: The partner ID if there is exactly one unique partner ID, the current
                      partner ID if the set is empty, or `None` if there are multiple partner IDs.

        """
        self.ensure_one()
        if len(lines_to_add_partner_ids) == 1:
            return lines_to_add_partner_ids.pop()
        if len(lines_to_add_partner_ids) == 0:
            return self.partner_id.id
        return None

    def _set_move_line_to_statement_line_move(self, lines_to_set, lines_to_add):
        """ Updates the bank statement line by setting the provided move lines
            (`lines_to_set`) and adding new move lines (`lines_to_add`). It also handles creating
            a counterpart move line if necessary and associates the correct partner and bank account
            details.

            :param lines_to_set: A recordset of move lines that are already associated
                                 with the bank statement line.
            :param lines_to_add: A list of dictionaries representing the move lines
                                 to be added to the bank statement line.
        """
        self.ensure_one()

        lines_to_add_balance = sum(line['balance'] for line in lines_to_add)
        lines_commands = [Command.set(lines_to_set.ids)] + [Command.create(line_to_add) for line_to_add in lines_to_add]

        open_balance = sum(lines_to_set.mapped('balance')) + lines_to_add_balance
        if not self.company_currency_id.is_zero(open_balance):
            lines_commands.append(Command.create(
                self._get_counterpart_aml(open_balance)
            ))
        move = self.move_id.with_context(force_delete=True, skip_readonly_check=True)
        move.line_ids = lines_commands
        partner_id = self._get_partner_id({line['partner_id'] for line in lines_to_add if line.get('partner_id')})
        partner = self.env['res.partner'].browse(partner_id)
        if partner and partner.company_id == partner.company_id.root_id:
            move.line_ids.filtered(lambda line: not line.partner_id).partner_id = partner

        # Create missing partner bank if necessary.
        if self.account_number and self.partner_id:
            self.with_context(
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
            ).partner_bank_id = self._find_or_create_bank_account()

    def _add_move_line_to_statement_line_move(self, lines_to_add):
        """ Adds move lines to the bank statement line and updates the reconciliation.

            :param lines_to_add: A list of move line values to be added to the bank statement line.
        """
        self.ensure_one()
        liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()
        self._set_move_line_to_statement_line_move(liquidity_lines + other_lines, lines_to_add)

    def set_partner_bank_statement_line(self, partner_id):
        """ Sets the partner for the bank statement line.

            :param partner_id: The ID of the partner to set on the bank statement line.
        """
        if self.partner_name:
            st_lines = self.search([('journal_id', '=', self.journal_id), ('partner_name', '=', self.partner_name), ('is_reconciled', '=', False), ('partner_id', '=', False)])
        else:
            st_lines = self
        st_lines.with_context(force_delete=True, skip_readonly_check=True).partner_id = partner_id
        st_lines._try_auto_reconcile_statement_lines()

    def set_account_bank_statement_line(self, aml_id, account_id):
        """ Sets the specified account to the given account move line.

            :param aml_id: The ID of the account move line to update.
            :param account_id: The ID of the account to set on the specified account move line.
        """
        account_move_line = self.line_ids.filtered(lambda line: line.id == aml_id)
        account_move_line.account_id = account_id

        self._handle_reconciliation_rule(account_move_line, account_id)
        self._check_and_create_reconciliation_rule(account_id, self.env.company.id)

    def _handle_reconciliation_rule(self, aml, account_id):
        # If a rule has been created by Odoo and is recommended to the user but another account is chosen, the rule
        # should be deleted.
        should_delete_rule = (
            aml.reconcile_model_id
            and aml.reconcile_model_id.create_uid.id == SUPERUSER_ID
            and account_id not in aml.reconcile_model_id.line_ids.account_id.ids
        )
        if should_delete_rule:
            aml.reconcile_model_id.sudo().unlink()

    def _check_and_create_reconciliation_rule(self, account_id, company_id):
        """Checks and creates reconciliation rules based on statement patterns."""
        if self._reconciliation_rule_exists(account_id, company_id):
            return

        bank_stmt_line_domain = [
            ('company_id', '=', company_id),
            ('journal_id', '=', self.journal_id.id),
            ('move_id.line_ids.account_id', '=', account_id),
            ('move_id.line_ids.reconcile_model_id', '=', False)
        ]
        previous_statement_lines = self.env['account.bank.statement.line'].search(
            bank_stmt_line_domain, limit=5, order='internal_index desc'
        )
        if len(previous_statement_lines) <= 1:
            return

        rule_data = self._prepare_reconciliation_rule_data(previous_statement_lines, account_id)
        if rule_data.get('common_substring_length') > 10:
            self._create_reconciliation_rule(rule_data)

    def _reconciliation_rule_exists(self, account_id, company_id):
        """Checks if a reconciliation rule already exists."""
        model_domain = (
                self.env['account.reconcile.model']._check_company_domain(company_id) +
                [('line_ids.account_id', '=', account_id), ('match_journal_ids', '=', self.journal_id.ids)]
        )
        return bool(self.env['account.reconcile.model'].search(model_domain, limit=1))

    def _prepare_reconciliation_rule_data(self, statement_lines, account_id):
        """Prepares data for reconciliation rule creation."""
        payment_refs = [line.payment_ref for line in statement_lines]
        amounts = [line.amount for line in statement_lines]
        common_substring = self._get_common_substring(payment_refs).strip()
        account = self.env['account.account'].browse(account_id)

        return {
            'name': account.name,
            'common_substring': common_substring,
            'common_substring_length': len(common_substring),
            'account': account,
            'partner_ids': statement_lines.partner_id.ids if len(statement_lines.partner_id.ids) == 1 else [],
            'amount': amounts[0] if len(set(amounts)) == 1 else None
        }

    def _create_reconciliation_rule(self, rule_data):
        """Creates a new reconciliation rule based on prepared data."""
        vals = {
            'name': rule_data['name'],
            'match_journal_ids': self.journal_id.ids,
            'match_label': 'match_regex',
            'match_label_param': rule_data['common_substring'],
            'line_ids': [
                Command.create({
                    'account_id': rule_data['account'].id,
                    'amount_type': 'percentage',
                    'amount_string': '100',
                    'label': rule_data['account'].name,
                }),
            ],
        }

        if rule_data['partner_ids']:
            vals['match_partner_ids'] = rule_data['partner_ids']

        if rule_data['amount'] is not None:
            vals.update({
                'match_amount': 'between',
                # The +- 0.01 is a hacky way to have "equal to" behaviour. This is due to the query that matches the
                # rules with the lines not having a separate condition for the "between", instead applying both
                # "greater" and "lower" conditions.
                'match_amount_min': rule_data['amount'] - 0.01,
                'match_amount_max': rule_data['amount'] + 0.01,
            })

        self.with_user(SUPERUSER_ID).with_company(self.journal_id.company_id).env['account.reconcile.model'].create(vals)

    def _get_common_substring(self, labels):
        def normalise_label(label):
            # Keep structured references.
            structured_refs = re.findall(r'\+{3}\d+/\d+/\d+\+{3}', label)
            placeholder_map = {}
            for idx, ref in enumerate(structured_refs):
                placeholder = f"__REF_{string.ascii_uppercase[idx]}__"
                label = label.replace(ref, placeholder)
                ref = ref.replace(r'+', r'\+')
                placeholder_map[placeholder] = ref

            label = re.sub(r'\d+', r'\\d+', label)

            # Put the structured references back.
            for placeholder, ref in placeholder_map.items():
                label = label.replace(placeholder, ref)

            return label

        def get_longest_common_substring(s1, s2):
            """
            Finds the longest common substring (LCS) between two input strings using dynamic programming.
            The function constructs a 2D table to keep track of suffix matches between the strings
            and identifies the LCS based on the maximum match length stored in the table.

            Parameters:
                s1 (str): The first input string.
                s2 (str): The second input string.

            Returns:
                str: The longest common substring found between `s1` and `s2`.
            """

            # Matrix to store lengths of common suffixes.
            dp = [[0] * (len(s2) + 1) for _ in range(len(s1) + 1)]

            longest = 0  # Length of the longest match.
            end_pos_s1 = 0  # End index in s1 where the longest match ends.

            # Build the matrix.
            for i in range(len(s1)):
                for j in range(len(s2)):
                    if s1[i] == s2[j]:
                        dp[i + 1][j + 1] = dp[i][j] + 1
                        if dp[i + 1][j + 1] > longest:
                            longest = dp[i + 1][j + 1]
                            end_pos_s1 = i + 1

            return s1[end_pos_s1 - longest:end_pos_s1]

        normalised = [normalise_label(label) for label in labels if label]
        # Sorting by length, so we start with the shortest strings first. This will allow us to exit early
        # if the size of the substring drops under 10.
        normalised.sort(key=len)

        # After normalising, we need to get the longest possible substring.
        # To do this, we get the one from the first two, then the result with the next string and so on.
        substring = get_longest_common_substring(normalised[0], normalised[1])
        for i in range(2, len(normalised)):
            if len(substring) < 10:
                break
            substring = get_longest_common_substring(substring, normalised[i])

        return substring

    def set_line_bank_statement_line(self, move_lines_ids):
        """ Sets the specified move lines to the bank statement line and performs reconciliation.

            :param move_lines_ids: A list of IDs for the move lines to be added to the bank statement line.
        """
        self.ensure_one()
        _liquidity_line, _suspense_lines, other_lines = self._seek_for_lines()

        transaction_amount, transaction_currency, journal_amount, journal_currency, company_amount, _company_currency = self._get_accounting_amounts_and_currencies()
        journal_transaction_rate = abs(transaction_amount / journal_amount) if journal_amount else 0.0
        company_transaction_rate = abs(transaction_amount / company_amount) if company_amount else 0.0

        open_balance = company_amount
        open_amount_currency = transaction_amount
        total_early_payment_discount = 0.0
        early_pay_aml_values_list = []
        move_lines = self.env['account.move.line'].browse(move_lines_ids)

        for line in other_lines + move_lines:
            # Early payment Discount
            if line.move_id._is_eligible_for_early_payment_discount(transaction_currency, self.date):
                total_early_payment_discount += line.amount_residual_currency - line.discount_amount_currency
                early_pay_aml_values_list.append({
                    'aml': line,
                    'amount_currency': -line.amount_residual_currency,
                    'balance': -line.amount_residual,
                })

            # move_lines are the lines coming from the reconcile button and other_lines are the lines from the bank
            # statement move. We need to invert the sign of move_lines since a positive move_line need to be put as
            # negative in the bank statement move.
            sign = -1 if line in move_lines else 1

            exchange_diff_balance = self._lines_get_account_balance_exchange_diff(line)
            line_balance = line.amount_residual + exchange_diff_balance
            open_balance += (line_balance * sign)

            if line.currency_id == transaction_currency:
                open_amount_currency += line.amount_residual_currency * sign
            elif line.currency_id == journal_currency:
                open_amount_currency += transaction_currency.round(line.amount_residual_currency * journal_transaction_rate) * sign
            else:
                open_amount_currency += transaction_currency.round(line_balance * company_transaction_rate) * sign

        new_lines = []
        is_early_payment_discount = False
        for move_line in move_lines:
            exchange_diff_balance = self._lines_get_account_balance_exchange_diff(move_line)
            current_balance = -(move_line.amount_residual + exchange_diff_balance)

            new_line_balance = current_balance
            new_amount_currency = -move_line.amount_residual_currency

            if partial_amounts := self._get_partial_amounts(current_balance, move_line, open_amount_currency, open_balance):
                new_line_balance = partial_amounts['partial_balance']
                new_amount_currency = partial_amounts['partial_amount_currency']

            if is_early_payment_discount := move_line.move_id._is_eligible_for_early_payment_discount(transaction_currency, self.date):
                new_line_balance = -move_line.amount_residual
                new_amount_currency = -move_line.amount_residual_currency

            new_lines.append(move_line._get_aml_values(
                balance=new_line_balance,
                amount_currency=new_amount_currency,
                currency_id=move_line.currency_id.id,
                reconciled_lines_ids=[Command.set(move_line.ids)],
            ))

        if is_early_payment_discount and open_amount_currency and self._qualifies_for_early_payment(transaction_currency, open_amount_currency, total_early_payment_discount):
            new_lines.extend(self._set_early_payment_discount_lines(early_pay_aml_values_list, open_balance))

        self._add_move_line_to_statement_line_move(new_lines)

    def _get_partial_amounts(self, current_balance, move_line, open_amount_currency, open_balance):
        def has_enough(currency, open_amount, current_amount):
            return (
                currency.compare_amounts(open_amount, 0) > 0
                and currency.compare_amounts(current_amount, 0) > 0
                and currency.compare_amounts(current_amount, open_amount) > 0
            )
        transaction_amount, transaction_currency, _journal_amount, _journal_currency, company_amount, company_currency = self._get_accounting_amounts_and_currencies()
        has_enough_comp_debit = has_enough(company_currency, open_balance, current_balance)
        has_enough_comp_credit = has_enough(company_currency, -open_balance, -current_balance)
        current_amount_currency = -move_line.amount_residual_currency
        has_enough_curr_debit = has_enough(move_line.currency_id, open_amount_currency, current_amount_currency)
        has_enough_curr_credit = has_enough(move_line.currency_id, -open_amount_currency, -current_amount_currency)

        if move_line.currency_id == transaction_currency and (has_enough_curr_debit or has_enough_curr_credit):
            new_amount_currency = (
                current_amount_currency
                # If the open amount is small, fully reconcile the move_line and not the transaction
                if move_line.currency_id.compare_amounts(abs(open_amount_currency), 0.03 * abs(current_amount_currency)) < 0
                else current_amount_currency - open_amount_currency
            )
            rate = abs(company_amount / transaction_amount) if transaction_amount else 0.0

            # Compute the amounts to make a partial.
            balance_after_partial = move_line.company_currency_id.round(new_amount_currency * rate)
            return {
                'partial_balance': balance_after_partial,
                'partial_amount_currency': new_amount_currency,
            }
        elif has_enough_comp_debit or has_enough_comp_credit:
            # Compute the new value for balance.
            balance_after_partial = (
                current_balance
                # If the open amount is small, fully reconcile the move_line and not the transaction
                if move_line.currency_id.compare_amounts(abs(open_balance), 0.03 * abs(current_balance)) < 0
                else current_balance - open_balance
            )
            # Get the rate of the original journal item.
            rate = move_line.currency_rate

            # Compute the amounts to make a partial.
            new_line_balance = move_line.company_currency_id.round(balance_after_partial * abs(move_line.amount_residual) / abs(current_balance))
            new_amount_currency = move_line.currency_id.round(new_line_balance * rate)
            return {
                'partial_balance': balance_after_partial,
                'partial_amount_currency': new_amount_currency,
            }
        return None

    def _lines_get_account_balance_exchange_diff(self, move_line):
        # Compute the balance of the line using the rate/currency coming from the bank transaction.
        amounts_in_st_curr = self._prepare_counterpart_amounts_using_st_line_rate(
            move_line.currency_id,
            move_line.amount_residual,
            move_line.amount_residual_currency,
        )
        transaction_currency_id = self.foreign_currency_id or self.currency_id
        origin_balance = amounts_in_st_curr['balance']
        if move_line.currency_id == self.company_currency_id and transaction_currency_id != self.company_currency_id:
            # The reconciliation will be expressed using the rate of the statement line.
            origin_balance = move_line.amount_residual
        elif move_line.currency_id != self.company_currency_id and transaction_currency_id == self.company_currency_id:
            # The reconciliation will be expressed using the foreign currency of the aml to cover the Mexican case.
            origin_balance = move_line.currency_id._convert(move_line.amount_residual_currency, transaction_currency_id, self.company_id, self.date)

        # Compute the exchange difference balance.
        return self.company_currency_id.round(origin_balance - move_line.amount_residual)

    @api.model
    def _qualifies_for_early_payment(self, transaction_currency, open_amount_currency, total_early_payment_discount):
        return transaction_currency.is_zero(open_amount_currency + total_early_payment_discount)

    def _set_early_payment_discount_lines(self, early_pay_aml_values_list, open_balance):
        early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(
            early_pay_aml_values_list,
            -open_balance,
        )
        new_lines = []

        for vals_list in early_payment_values.values():
            for vals in vals_list:
                new_lines.append({
                    'account_id': vals['account_id'],
                    'date': self.date,
                    'name': vals['name'],
                    'partner_id': vals['partner_id'],
                    'currency_id': vals['currency_id'],
                    'amount_currency': vals['amount_currency'],
                    'balance': vals['balance'],
                    'analytic_distribution': vals.get('analytic_distribution'),
                    'tax_ids': vals.get('tax_ids', []),
                    'tax_tag_ids': vals.get('tax_tag_ids', []),
                    'tax_repartition_line_id': vals.get('tax_repartition_line_id'),
                    'group_tax_id': vals.get('group_tax_id'),
                })
        return new_lines

    def delete_reconciled_line(self, move_line_ids):
        """ Deletes the specified move lines from the bank statement line after unreconciling them.

            :param move_line_ids: A list of move line IDs to be deleted.
        """
        self.ensure_one()
        move_lines_to_remove = self.env['account.move.line'].browse(move_line_ids)
        liquidity_line, _suspense_lines, other_lines = self._seek_for_lines()

        move_lines_to_remove.remove_move_reconcile()
        self._set_move_line_to_statement_line_move(
            liquidity_line + other_lines - move_lines_to_remove,
            [],
        )

    def edit_reconcile_line(self, move_line_id, record_data):
        """ Edits the specified move line from the bank statement line with the given data.
            We can only edit line that are not linked to a move line.

            :param move_line_id: The ID of the move line to be edited.
            :param record_data: A dictionary containing the data to update the move line with.
        """
        self.ensure_one()
        move_line_to_edit = self.env['account.move.line'].browse(move_line_id)
        liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()

        edited_move_reconciled_line_ids = move_line_to_edit.reconciled_lines_ids.ids
        move_line_to_edit.remove_move_reconcile()
        move_line_to_edit_vals = move_line_to_edit._get_aml_values(**record_data)
        if edited_move_reconciled_line_ids:
            move_line_to_edit_vals['reconciled_lines_ids'] = [Command.set(edited_move_reconciled_line_ids)]

        self._set_move_line_to_statement_line_move(
            (liquidity_lines + other_lines) - move_line_to_edit,
            [move_line_to_edit_vals],
        )

        if record_data.get('tax_ids'):
            self._recompute_tax_lines()

    def _recompute_tax_lines(self):
        self.ensure_one()
        liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()
        other_lines.filtered(lambda line: not line.reconciled_lines_ids)  # We do not recompute tax on lines that come from invoice

        AccountTax = self.env['account.tax']
        base_amls = other_lines.filtered(lambda line: not line.tax_repartition_line_id)
        base_lines = [self._prepare_base_line_for_taxes_computation(line) for line in base_amls]
        tax_amls = other_lines - base_amls
        tax_lines = [self._prepare_tax_line_for_taxes_computation(line) for line in tax_amls]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, self.company_id, include_caba_tags=True)
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id, tax_lines=tax_lines)

        lines_to_delete = self.env['account.move.line']
        lines_to_add_or_update = []

        # Update the base lines.
        for base_line, to_update in tax_results['base_lines_to_update']:
            line = base_line['record']
            amount_currency = to_update['amount_currency']
            balance = self._prepare_counterpart_amounts_using_st_line_rate(line.currency_id, line.amount_residual, amount_currency)['balance']
            lines_to_delete += line
            lines_to_add_or_update.append(line._get_aml_values(balance=balance, amount_currency=amount_currency, tax_tag_ids=to_update['tax_tag_ids']))

        # Tax lines that are no longer needed.
        for tax_line_vals in tax_results['tax_lines_to_delete']:
            lines_to_delete += tax_line_vals['record']

        # Newly created tax lines.
        for tax_line_vals in tax_results['tax_lines_to_add']:
            lines_to_add_or_update.append(self._lines_prepare_tax_line(tax_line_vals))

        # Update of existing tax lines.
        for tax_line_vals, grouping_key, to_update in tax_results['tax_lines_to_update']:
            lines_to_delete += tax_line_vals['record']
            new_line_vals = self._lines_prepare_tax_line({**grouping_key, **to_update})
            lines_to_add_or_update.append(tax_line_vals['record']._get_aml_values(**new_line_vals))

        lines_to_keep = (liquidity_lines + other_lines) - lines_to_delete
        self._set_move_line_to_statement_line_move(lines_to_keep, lines_to_add_or_update)

    def _lines_prepare_tax_line(self, tax_line_vals):
        self.ensure_one()

        tax_rep = self.env['account.tax.repartition.line'].browse(tax_line_vals['tax_repartition_line_id'])
        name = tax_rep.tax_id.name
        if self.payment_ref:
            name = f'{name} - {self.payment_ref}'
        currency = self.env['res.currency'].browse(tax_line_vals['currency_id'])
        amount_currency = tax_line_vals['amount_currency']
        balance = self._prepare_counterpart_amounts_using_st_line_rate(currency, None, amount_currency)['balance']

        return {
            'account_id': tax_line_vals['account_id'],
            'date': self.date,
            'name': name,
            'partner_id': tax_line_vals['partner_id'],
            'currency_id': currency.id,
            'amount_currency': amount_currency,
            'balance': balance,
            'analytic_distribution': tax_line_vals['analytic_distribution'],
            'tax_repartition_line_id': tax_rep.id,
            'tax_ids': tax_line_vals['tax_ids'],
            'tax_tag_ids': tax_line_vals['tax_tag_ids'],
            'group_tax_id': tax_line_vals['group_tax_id'],
        }

    def _prepare_base_line_for_taxes_computation(self, line_vals):
        """ Convert the current dictionary to use the generic taxes computation method defined on account.tax.

            :returns: A dictionary representing a base line.
        """
        self.ensure_one()
        if not line_vals:
            return {}

        tax_type = line_vals.tax_ids[0].type_tax_use if line_vals.tax_ids else None
        is_refund = (tax_type == 'sale' and line_vals.balance > 0.0) or (tax_type == 'purchase' and line_vals.balance < 0.0)

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            line_vals,
            price_unit=line_vals.amount_currency,
            quantity=1.0,
            is_refund=is_refund,
            special_mode='total_included',
        )

    def _prepare_tax_line_for_taxes_computation(self, line):
        """ Convert the current dictionary to use the generic taxes computation method defined on account.tax.

            :return: A dictionary representing a tax line.
        """
        self.ensure_one()
        if not line:
            return {}
        return self.env['account.tax']._prepare_tax_line_for_taxes_computation(line)

    def create_document_from_attachment(self, attachment_ids):
        """ Create the invoices from files.
            :return: A action redirecting to account.move list/form view.
        """
        statement_line = self.browse(self.env.context.get("statement_line_id"))

        purchase_journal_id = self.env['account.journal'].search_fetch(
            domain=[*self.env['account.journal']._check_company_domain(statement_line.company_id), ('type', '=', 'purchase')],
            field_names=['id'],
            limit=1,
        )
        invoices = purchase_journal_id.with_context(default_move_type="in_invoice")._create_document_from_attachment(attachment_ids)
        return invoices._get_records_action()

    def action_unreconcile_entry(self):
        self.ensure_one()

        _liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()
        other_lines.remove_move_reconcile()

    @api.model_create_multi
    def create(self, vals_list):
        statement_lines = super().create(vals_list)
        for statement_line in statement_lines:
            if statement_line.transaction_details:
                statement_line.move_id.message_post(body=statement_line._format_transaction_details())

            if not statement_line.partner_id and not self.env.context.get('no_retrieve_partner'):
                # TODO post-freeze: batch processing
                statement_line.with_context(force_delete=True, skip_readonly_check=True).partner_id = statement_line._retrieve_partner()

        # process automatically the new lines in case we pass some context key (i.e coming from the bank reconciliation widget)
        if self.env.context.get('auto_statement_processing', False) and statement_lines:
            statement_lines._try_auto_reconcile_statement_lines()
        return statement_lines

    def _format_transaction_details(self):
        """ Format the 'transaction_details' field of the statement line to be more readable for the end user.

        Example:
            {
                "debtor": {
                    "name": None,
                    "private_id": None,
                },
                "debtor_account": {
                    "iban": "BE84103080286059",
                    "bank_transaction_code": None,
                    "credit_debit_indicator": "DBIT",
                    "status": "BOOK",
                    "value_date": "2022-12-29",
                    "transaction_date": None,
                    "balance_after_transaction": None,
                },
            }

        Becomes:
            debtor_account:
                iban: BE84103080286059
                credit_debit_indicator: DBIT
                status: BOOK
                value_date: 2022-12-29

        :returns: An html representation of the transaction details.
        """
        self.ensure_one()
        details = self.transaction_details
        if not details:
            return

        def _get_formatted_data(data, prefix=""):
            keys = data.keys() if isinstance(data, dict) else [i for i, _ in enumerate(data)]
            result = Markup()
            for key in keys:
                value = data[key]
                result += prefix + Markup("<b>%s:</b> ") % str(key)
                if isinstance(value, (list, dict)):
                    result += "\n"
                    result += _get_formatted_data(value, prefix + "  ")
                    continue
                result += str(value) + "\n"
            return result

        res = _get_formatted_data(details)
        return Markup("<div><pre>%s</pre></div>") % res

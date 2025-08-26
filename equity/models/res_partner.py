from dateutil.relativedelta import relativedelta
import json
import uuid

from odoo import api, fields, models
from odoo.tools.misc import format_date


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    equity_access_token = fields.Char(groups=fields.NO_ACCESS, prefetch=False, copy=False)

    # Investee (Company) fields
    equity_transaction_ids = fields.One2many('equity.transaction', 'partner_id')
    equity_transaction_count = fields.Integer(compute='_compute_transaction_count')
    equity_currency_id = fields.Many2one('res.currency', string="Equity Currency", default=lambda self: self.env.company.currency_id)

    equity_shareholders_count = fields.Integer(compute='_compute_shareholders_count')
    equity_authorized_rep_count = fields.Integer(compute='_compute_authorized_rep_count')

    equity_last_valuation = fields.Monetary(compute='_compute_equity_last_valuation', currency_field='equity_currency_id')
    equity_kanban_dashboard_graph = fields.Text(compute='_compute_equity_kanban_dashboard_graph')

    # Investee (Company) methods
    def _compute_transaction_count(self):
        partners_transactions = dict(self.env['equity.transaction']._read_group(
            domain=[('partner_id', 'in', self.ids)],
            groupby=['partner_id'],
            aggregates=['__count'],
        ))
        for partner in self:
            partner.equity_transaction_count = partners_transactions.get(partner, 0)

    def _compute_shareholders_count(self):
        partners_holders = dict(self.env['equity.cap.table']._read_group(
            domain=[('partner_id', 'in', self.ids)],
            groupby=['partner_id'],
            aggregates=['holder_id:count_distinct'],
        ))
        for partner in self:
            partner.equity_shareholders_count = partners_holders.get(partner, 0)

    def _compute_authorized_rep_count(self):
        auth_rep_dict = dict(self.env['equity.authorized.rep']._read_group(
            domain=[('partner_id', 'in', self.ids)],
            groupby=['partner_id'],
            aggregates=['__count'],
        ))
        for partner in self:
            partner.equity_authorized_rep_count = auth_rep_dict.get(partner, 0)

    def _compute_equity_last_valuation(self):
        for partner in self:
            last_valuation_id = self.env['equity.valuation'].search([('partner_id', '=', partner.id), ('date', '<=', fields.Date.today())], order='date DESC', limit=1)
            partner.equity_last_valuation = 0 if not last_valuation_id else last_valuation_id.valuation

    def _compute_equity_kanban_dashboard_graph(self):
        for partner in self:
            partner_valuations = self.env['equity.valuation'].search([('partner_id', '=', partner.id)], order='date ASC')
            values = [
                {
                    'x': format_date(self.env, partner_valuations[0].date - relativedelta(days=1), date_format='d LLLL Y'),
                    'y': 0,
                },
                *[
                    {
                        'x': format_date(self.env, partner_valuation.date, date_format='d LLLL Y'),
                        'y': partner_valuation.valuation,
                    } for partner_valuation in partner_valuations
                ],
            ] if partner_valuations else [{
                'x': '',
                'y': (2 ** i) - 1,
            } for i in range(6)]
            partner.equity_kanban_dashboard_graph = json.dumps([{
                'values': values,
                'title': '',
                'key': self.env._("Valuation"),
                'is_sample_data': not len(partner_valuations),
            }])

    # cap table methods
    def _get_cap_table_data(self):
        self.ensure_one()
        return {
            'display_name': self.display_name,
            'equity_currency_id': self.equity_currency_id.id,
        }

    @api.model
    def open_equity_dashboard(self):
        partners_with_transactions = self.search([('equity_transaction_ids', '!=', False)], limit=2)
        if len(partners_with_transactions) <= 1:
            return partners_with_transactions.action_open_cap_table()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Equity"),
            'res_model': 'res.partner',
            'view_mode': 'kanban',
            'views': [(False, 'kanban')],
            'view_id': self.env.ref('equity.equity_dashboard_res_partner').id,
            'domain': [('equity_transaction_ids', '!=', False)],
        }

    def action_open_cap_table(self):
        return {
            **self.env['ir.actions.actions']._for_xml_id('equity.action_equity_cap_table'),
            'display_name': self.env._("Cap Table"),
            'context': {
                'active_ids': self.ids,
            },
        }

    def action_open_transaction_list(self):
        self.ensure_one()
        return {
            **self.equity_transaction_ids._get_records_action(),
            'display_name': self.env._("%(partner_name)s's Transactions", partner_name=self.name),
        }

    # misc methods
    def _equity_ensure_token(self):
        """ Get the current record equity access token """
        if not self.equity_access_token:
            # we use a `write` to force the cache clearing otherwise `return self.access_token` will return False
            self.sudo().write({'equity_access_token': str(uuid.uuid4())})
        return f"{self.id}${self.equity_access_token}"

    def action_partner_send(self, linked_transaction=None):
        self.ensure_one()
        linked_transaction = linked_transaction or self.env['equity.transaction'].search([
            ('date', '<=', fields.Date.context_today(self)),
            '|', ('subscriber_id', '=', self.id), ('seller_id', '=', self.id),
        ], order='date DESC', limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Invite %s", self.name),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'view_id': self.env.ref('equity.equity_email_compose_message_wizard_form').id,
            'target': 'new',
            'context': {
                'default_model': 'equity.transaction',
                'default_res_ids': linked_transaction.ids,
                'default_partner_ids': self.ids,
                'default_template_id': self.env.ref('equity.equity_shareholder_email_template').id,
                'default_composition_mode': 'comment',
                'hide_recipients': True,
                'holder_name': self.name,
                'equity_access_token': self.sudo()._equity_ensure_token(),
            },
        }

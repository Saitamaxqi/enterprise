import uuid

from odoo import fields, models


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

    # cap table methods
    def _get_cap_table_data(self):
        self.ensure_one()
        return {
            'display_name': self.display_name,
            'equity_currency_id': self.equity_currency_id.id,
        }

    def action_open_cap_table(self):
        self.ensure_one()
        return {
            **self.env['ir.actions.actions']._for_xml_id('equity.action_equity_cap_table'),
            'display_name': self.env._("%(partner_name)s's Cap Table", partner_name=self.name),
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

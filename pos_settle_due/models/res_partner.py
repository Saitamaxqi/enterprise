# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_total_due(self, config_id):
        config = self.env['pos.config'].browse(config_id)
        pos_payments = self.env['pos.order'].search([
            ('partner_id', '=', self.id), ('state', '=', 'paid'),
            ('session_id.state', '!=', 'closed')]).mapped('payment_ids')
        total_settled = sum(pos_payments.filtered_domain(
            [('payment_method_id.type', '=', 'pay_later')]).mapped('amount'))

        total_due = self.parent_id.total_due if self.parent_id else self.total_due
        total_due += total_settled
        if self.env.company.currency_id.id != config.currency_id.id:
            pos_currency = config.currency_id
            total_due = self.env.company.currency_id._convert(total_due, pos_currency, self.env.company, fields.Date.today())
        partner = self.read(self._load_pos_data_fields(config_id), load=False)[0]
        partner['total_due'] = total_due
        return {
            'res.partner': [partner],
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.user.has_group('account.group_account_readonly') or self.env.user.has_group('account.group_account_invoice'):
            params += ['credit_limit', 'total_due', 'use_partner_credit_limit']
        return params

    def _load_pos_data(self, data):
        response = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config'][0]['id'])

        if config_id.currency_id != self.env.company.currency_id and (self.env.user.has_group('account.group_account_readonly') or self.env.user.has_group('account.group_account_invoice')):
            for partner in response:
                partner['total_due'] = self.env.company.currency_id._convert(partner['total_due'], config_id.currency_id, self.env.company, fields.Date.today())

        return response

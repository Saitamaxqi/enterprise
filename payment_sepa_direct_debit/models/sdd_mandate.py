# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import SUPERUSER_ID, models


_logger = logging.getLogger(__name__)

INT_PHONE_NUMBER_FORMAT_REGEX = r'^\+[^+]+$'


class SddMandate(models.Model):
    _inherit = 'sdd.mandate'

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') in ['closed', 'revoked']:
            linked_tokens = self.env['payment.token'].search([('sdd_mandate_id', 'in', self.ids)])
            linked_tokens.active = False
        return res

    def _confirm(self):
        """ Confirm the customer's ownership of the SEPA Direct Debit mandate. """
        template = self.env.ref('payment_sepa_direct_debit.mail_template_sepa_notify_validation')
        self.write({'state': 'active'})
        template.with_user(SUPERUSER_ID).send_mail(self.id)

    def action_validate_mandate(self):
        """ Override of `account_sepa_direct_debit` to create a token when validating mandates."""
        super().action_validate_mandate()
        sepa_provider_per_company = dict(self.env['payment.provider']._read_group([
            *self.env['payment.provider']._check_company_domain(self.company_id),
            ('custom_mode', '=', 'sepa_direct_debit'),
            ('is_published', '=', True),
            ('state', '!=', 'disabled'),
        ], groupby=['company_id'], aggregates=['id:recordset']))
        for mandate in self.filtered(lambda m: m.state == 'active'):
            provider = sepa_provider_per_company.get(mandate.company_id)
            if provider:
                provider[:1]._sdd_create_token_for_mandate(mandate.partner_id, mandate)

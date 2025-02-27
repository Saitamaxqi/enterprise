# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class MarketingAutomationWACase(common.TransactionCase):

    @classmethod
    def setUpWhatsapp(cls):
        cls.tracked_url = 'https://www.tracked.com'
        cls.dynamic_url = 'https://www.dynamic.com'
        cls.test_wa_template = cls.env['whatsapp.template'].create({
            'body': 'Hello {{1}}',
            'button_ids': [
                (0, 0, {
                    'button_type': 'url',
                    'name': 'tracked url',
                    'sequence': 0,
                    'url_type': 'tracked',
                    'website_url': cls.tracked_url,
                }),
                (0, 0, {
                    'sequence': 1,
                    'button_type': 'url',
                    'name': 'dynamic url',
                    'url_type': 'dynamic',
                    'website_url': cls.dynamic_url,
                }),
            ],
            'name': 'Test-dynamic',
            'status': 'approved',
            'variable_ids': [
                (0, 0, {
                    'name': "{{1}}", 'line_type': "body", 'field_type': 'free_text', 'demo_value': cls.tracked_url,
                }),
            ],
            'wa_account_id': cls.whatsapp_account.id,
        })

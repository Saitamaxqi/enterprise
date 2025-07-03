from odoo.exceptions import UserError
from odoo.fields import Command

from odoo.addons.equity.tests.common import TestEquityCommon


class TestEquity(TestEquityCommon):
    def test_no_transaction(self):
        self.assertFalse(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]))

    def test_shares_equal_class(self):
        self.env['equity.transaction'].create([
            {
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 75,
                'security_price': 10,
                'share_class_id': self.share_class_ord.id,
            },
            {
                'partner_id': self.company.id,
                'subscriber_id': self.contact_2.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 25,
                'security_price': 7,
                'share_class_id': self.share_class_ord.id,
            },
        ])
        self.assertRecordValues(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]), [
            {
                'partner_id': self.company.id,
                'holder_id': self.contact_1.id,
                'shares': 75,
                'options': 0,
                'votes': 75,
                'ownership': 0.75,
                'voting_rights': 0.75,
                'shares_dilution': 0.75,
                'options_dilution': 0,
                'shares_valuation': 750,
                'options_valuation': 0,
            },
            {
                'partner_id': self.company.id,
                'holder_id': self.contact_2.id,
                'shares': 25,
                'options': 0,
                'votes': 25,
                'ownership': 0.25,
                'voting_rights': 0.25,
                'shares_dilution': 0.25,
                'options_dilution': 0,
                'shares_valuation': 250,
                'options_valuation': 0,
            },
        ])

    def test_share_more_vote(self):
        self.env['equity.transaction'].create([
            {
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 100,
                'security_price': 10,
                'share_class_id': self.share_class_a.id,
            },
            {
                'partner_id': self.company.id,
                'subscriber_id': self.contact_2.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 100,
                'security_price': 10,
                'share_class_id': self.share_class_b.id,
            },
        ])
        self.assertRecordValues(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]), [
            {
                'partner_id': self.company.id,
                'holder_id': self.contact_1.id,
                'shares': 100,
                'options': 0,
                'votes': 200,
                'ownership': 0.5,
                'voting_rights': 0.66666666666666666666666,
                'shares_dilution': 0.5,
                'options_dilution': 0,
                'shares_valuation': 500,
                'options_valuation': 0,
            },
            {
                'partner_id': self.company.id,
                'holder_id': self.contact_2.id,
                'shares': 100,
                'options': 0,
                'votes': 100,
                'ownership': 0.5,
                'voting_rights': 0.33333333333333333333333,
                'shares_dilution': 0.5,
                'options_dilution': 0,
                'shares_valuation': 500,
                'options_valuation': 0,
            },
        ])

    def test_sell_shares(self):
        self.env['equity.transaction'].create([
            {
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 100,
                'security_price': 10,
                'share_class_id': self.share_class_ord.id,
            },
            {
                'partner_id': self.company.id,
                'seller_id': self.contact_1.id,
                'subscriber_id': self.contact_2.id,
                'date': '2011-01-01',
                'transaction_type': 'sale',
                'securities': 30,
                'security_price': 10,
                'share_class_id': self.share_class_ord.id,
            },
        ])
        self.assertRecordValues(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]), [
            {
                'partner_id': self.company.id,
                'holder_id': self.contact_1.id,
                'shares': 70,
                'options': 0,
                'votes': 70,
                'ownership': 0.7,
                'voting_rights': 0.7,
                'shares_dilution': 0.7,
                'options_dilution': 0,
                'shares_valuation': 700,
                'options_valuation': 0,
            },
            {
                'partner_id': self.company.id,
                'holder_id': self.contact_2.id,
                'shares': 30,
                'options': 0,
                'votes': 30,
                'ownership': 0.3,
                'voting_rights': 0.3,
                'shares_dilution': 0.3,
                'options_dilution': 0,
                'shares_valuation': 300,
                'options_valuation': 0,
            },
        ])

    def test_option_expired(self):
        self.env['equity.transaction'].create([{
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '1900-01-01',
                'expiration_date': '1901-12-31',
                'transaction_type': 'option',
                'securities': 100,
                'security_price': 10,
                'share_class_id': self.share_class_ord.id,
        }])
        self.assertRecordValues(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]), [{
            'partner_id': self.company.id,
            'holder_id': self.contact_1.id,
            'shares': 0,
            'options': 0,
            'votes': 0,
            'ownership': 0,
            'voting_rights': 0,
            'shares_dilution': 0,
            'options_dilution': 0,
            'shares_valuation': 0,
            'options_valuation': 0,
        }])

    def test_option_into_share_exceed(self):
        # Issue options
        option_issuance = self.env['equity.transaction'].create([{
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '2010-01-01',
                'expiration_date': '2100-12-31',
                'transaction_type': 'option',
                'securities': 100,
                'security_price': 10,
                'share_class_id': self.share_class_ord.id,
                'child_transaction_ids': [
                    Command.create({
                        'partner_id': self.company.id,
                        'subscriber_id': self.contact_1.id,
                        'date': '2010-01-01',
                        'transaction_type': 'share',
                        'securities': 20,
                        'security_price': 10,
                        'share_class_id': self.share_class_ord.id,
                    }),
                ],
        }])

        with self.assertRaisesRegex(UserError, "options available"):
            self.env['equity.transaction'].create([{
                'parent_transaction_id': option_issuance.id,
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 90,
                'security_price': 10,
                'share_class_id': self.share_class_ord.id,
            }])

    def test_option_into_share_different_class(self):
        # Issue options
        option_issuance = self.env['equity.transaction'].create([{
            'partner_id': self.company.id,
            'subscriber_id': self.contact_1.id,
            'date': '2010-01-01',
            'expiration_date': '2100-12-31',
            'transaction_type': 'option',
            'securities': 100,
            'security_price': 10,
            'share_class_id': self.share_class_ord.id,
        }])

        with self.assertRaisesRegex(UserError, "must have the same"):
            self.env['equity.transaction'].create([{
                'parent_transaction_id': option_issuance.id,
                'partner_id': self.company.id,
                'subscriber_id': self.contact_1.id,
                'date': '2010-01-01',
                'transaction_type': 'share',
                'securities': 20,
                'security_price': 10,
                'share_class_id': self.share_class_a.id,
            }])

    def test_option_into_share(self):
        # Issue options
        option_issuance = self.env['equity.transaction'].create([{
            'partner_id': self.company.id,
            'subscriber_id': self.contact_1.id,
            'date': '2010-01-01',
            'expiration_date': '2100-12-31',
            'transaction_type': 'option',
            'securities': 100,
            'security_price': 10,
            'share_class_id': self.share_class_ord.id,
        }])
        self.assertRecordValues(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]), [{
            'partner_id': self.company.id,
            'holder_id': self.contact_1.id,
            'shares': 0,
            'options': 100,
            'votes': 0,
            'ownership': 0,
            'voting_rights': 0,
            'shares_dilution': 0,
            'options_dilution': 1,
            'shares_valuation': 0,
            'options_valuation': 1000,
        }])

        # Exercise options
        self.env['equity.transaction'].create([{
            'parent_transaction_id': option_issuance.id,
            'partner_id': self.company.id,
            'subscriber_id': self.contact_1.id,
            'date': '2011-01-01',
            'transaction_type': 'share',
            'securities': 20,
            'security_price': 10,
            'share_class_id': self.share_class_ord.id,
        }])
        self.assertEqual(option_issuance.remaining_options, 80)
        self.assertRecordValues(self.env['equity.cap.table'].search([('partner_id', '=', self.company.id)]), [{
            'partner_id': self.company.id,
            'holder_id': self.contact_1.id,
            'shares': 20,
            'options': 80,
            'votes': 20,
            'ownership': 1,
            'voting_rights': 1,
            'shares_dilution': 0.2,
            'options_dilution': 0.8,
            'shares_valuation': 200,
            'options_valuation': 800,
        }])

        # Looking in the past, it should still display the old value
        self.assertRecordValues(
            self.env['equity.cap.table'].with_context(current_date='2010-01-01').search([('partner_id', '=', self.company.id)]),
            [{
                'partner_id': self.company.id,
                'holder_id': self.contact_1.id,
                'shares': 0,
                'options': 100,
                'votes': 0,
                'ownership': 0,
                'voting_rights': 0,
                'shares_dilution': 0,
                'options_dilution': 1,
                'shares_valuation': 0,
                'options_valuation': 1000,
            }],
        )

        # Looking past the expiry shouldn't display the options anymore
        self.assertRecordValues(
            self.env['equity.cap.table'].with_context(current_date='2200-01-01').search([('partner_id', '=', self.company.id)]),
            [{
                'partner_id': self.company.id,
                'holder_id': self.contact_1.id,
                'shares': 20,
                'options': 0,
                'votes': 20,
                'ownership': 1,
                'voting_rights': 1,
                'shares_dilution': 1,
                'options_dilution': 0,
                'shares_valuation': 1000,
                'options_valuation': 0,
            }],
        )

from datetime import date
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


def patched_generate_all_returns(account_return_type, country_code, main_company, tax_unit=None):
    TestAccountReturn.basic_return_type._try_create_returns_for_fiscal_year(main_company, tax_unit)


@tagged('post_install', '-at_install')
class TestAccountReturn(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # necessary to ensure successful return checks
        cls.company_data['company'].write({
            'vat': 'US12345671',
            'phone': '123456789',
            'email': 'test@gmail.com',
        })

        cls.basic_return_type = cls.env['account.return.type'].create({
            'name': 'VAT Return (Generic)',
            'report_id': cls.env.ref('account.generic_tax_report').id,
            'deadline_start_date': '2024-01-01'
        })

        cls.startClassPatcher(freeze_time('2024-01-01'))

        with cls._patch_returns_generation():
            cls.env.company.account_opening_date = '2024-01-01'

    @classmethod
    def _patch_returns_generation(cls):
        return patch.object(cls.registry('account.return.type'), '_generate_all_returns', patched_generate_all_returns)

    def assert_return_dates_equal(self, returns, dates_list):
        self.assertEqual(len(returns), len(dates_list), "Return count mismatch")

        errors = []
        for i, account_return in enumerate(returns):
            dates_tuple = dates_list[i]
            if fields.Date.to_string(account_return.date_from) != dates_tuple[0]:
                errors += [
                    f"\n==== Differences at index {i} ====",
                    f"Current date_from:  {account_return.date_from}",
                    f"Expected date_from: {dates_tuple[0]}",
                ]
            if fields.Date.to_string(account_return.date_to) != dates_tuple[1]:
                errors += [
                    f"\n==== Differences at index {i} ====",
                    f"Current date_to:  {account_return.date_to}",
                    f"Expected date_to: {dates_tuple[1]}",
                ]
        if errors:
            self.fail('\n'.join(errors))

    def test_return_generation_normal(self):
        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
            ]
        )

    def test_return_generation_change_periodicity_smaller_to_greater(self):
        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        # Submitting this one ("2025-01-01", "2025-01-31")
        with self.allow_pdf_render():
            existing_returns[0].action_submit()

        # Regenerate new returns without overriding posted ones
        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = '2_months'

        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-01-31"),  # First one already posted
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
            ]
        )

    def test_return_generation_change_periodicity_greater_to_smaller(self):
        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = '2_months'

        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
            ]
        )

        # Submitting this one ("2024-01-01", "2024-02-28")
        with self.allow_pdf_render():
            existing_returns[0].action_submit()

        # Regenerate new returns without overriding posted ones
        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = 'monthly'

        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-02-29"),  # First one already posted
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
            ]
        )

    def test_return_generation_with_start_date(self):
        with self._patch_returns_generation():
            self.basic_return_type.deadline_start_date = '2024-12-01'
            self.env.company.account_return_periodicity = '4_months'

        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2023-12-01", "2024-03-31"),   # out of fy start
                ("2024-04-01", "2024-07-31"),
                ("2024-08-01", "2024-11-30"),
            ]
        )

    def test_return_generation_with_start_date_and_periodicity_change(self):
        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])
        # Submitting this one ("2024-01-01", "2024-01-31")
        with self.allow_pdf_render():
            existing_returns[0].action_submit()

        with self._patch_returns_generation():
            self.basic_return_type.deadline_start_date = '2024-12-01'
            self.env.company.account_return_periodicity = '4_months'

        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-01-31"),   # first already posted so we won't create another one before it
                ("2024-04-01", "2024-07-31"),
                ("2024-08-01", "2024-11-30"),
            ]
        )

    def test_return_generation_with_all_return_posted(self):
        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])

        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
            ]
        )

        for existing_return in existing_returns:
            existing_return.action_mark_completed()

        self.assertRecordValues(
            existing_returns,
            [
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
                {'is_completed': True},
            ]
        )

        with self._patch_returns_generation():
            self.env.company.account_return_periodicity = 'trimester'

        existing_returns = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.env.company.id)
        ])
        self.assert_return_dates_equal(
            existing_returns,
            [
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
            ]
        )

    def test_period_boundaries_generation(self):
        def assert_period(input_date, expected_start, expected_end):
            period_start, period_end = self.basic_return_type._get_period_boundaries(self.env.company, input_date)
            self.assertEqual(period_start, expected_start, f"Period start date ({fields.Date.to_string(period_start)}) doesn't match the expected period start date: ({fields.Date.to_string(expected_start)})")
            self.assertEqual(period_end, expected_end, f"Period end date ({fields.Date.to_string(period_end)}) doesn't match the expected period end date: ({fields.Date.to_string(expected_end)})")

        # Periodicity only with default start_date
        self.env.company.account_return_periodicity = 'monthly'
        assert_period(date(2024, 1, 1), expected_start=date(2024, 1, 1), expected_end=date(2024, 1, 31))
        assert_period(date(2024, 9, 30), expected_start=date(2024, 9, 1), expected_end=date(2024, 9, 30))
        assert_period(date(2024, 10, 1), expected_start=date(2024, 10, 1), expected_end=date(2024, 10, 31))

        self.env.company.account_return_periodicity = 'trimester'
        assert_period(date(2024, 1, 1), expected_start=date(2024, 1, 1), expected_end=date(2024, 3, 31))
        assert_period(date(2024, 5, 1), expected_start=date(2024, 4, 1), expected_end=date(2024, 6, 30))
        assert_period(date(2024, 9, 30), expected_start=date(2024, 7, 1), expected_end=date(2024, 9, 30))
        assert_period(date(2024, 10, 1), expected_start=date(2024, 10, 1), expected_end=date(2024, 12, 31))

        self.env.company.account_return_periodicity = 'year'
        assert_period(date(2024, 1, 1), expected_start=date(2024, 1, 1), expected_end=date(2024, 12, 31))
        assert_period(date(2023, 12, 31), expected_start=date(2023, 1, 1), expected_end=date(2023, 12, 31))

        # Basic start dates
        self.env.company.account_return_periodicity = 'trimester'
        self.basic_return_type.deadline_start_date = '2024-01-01'
        assert_period(date(2024, 1, 1), expected_start=date(2024, 1, 1), expected_end=date(2024, 3, 31))
        assert_period(date(2024, 4, 1), expected_start=date(2024, 4, 1), expected_end=date(2024, 6, 30))
        assert_period(date(2024, 5, 1), expected_start=date(2024, 4, 1), expected_end=date(2024, 6, 30))
        assert_period(date(2024, 9, 30), expected_start=date(2024, 7, 1), expected_end=date(2024, 9, 30))
        assert_period(date(2024, 10, 1), expected_start=date(2024, 10, 1), expected_end=date(2024, 12, 31))

        self.basic_return_type.deadline_start_date = '2024-02-01'
        assert_period(date(2024, 1, 1), expected_start=date(2023, 11, 1), expected_end=date(2024, 1, 31))
        assert_period(date(2024, 1, 31), expected_start=date(2023, 11, 1), expected_end=date(2024, 1, 31))
        assert_period(date(2024, 2, 1), expected_start=date(2024, 2, 1), expected_end=date(2024, 4, 30))
        assert_period(date(2024, 6, 1), expected_start=date(2024, 5, 1), expected_end=date(2024, 7, 31))
        assert_period(date(2024, 10, 31), expected_start=date(2024, 8, 1), expected_end=date(2024, 10, 31))
        assert_period(date(2024, 11, 1), expected_start=date(2024, 11, 1), expected_end=date(2025, 1, 31))

        self.env.company.account_return_periodicity = 'monthly'
        assert_period(date(2024, 2, 1), expected_start=date(2024, 2, 1), expected_end=date(2024, 2, 29))
        assert_period(date(2024, 1, 31), expected_start=date(2024, 1, 1), expected_end=date(2024, 1, 31))
        assert_period(date(2024, 1, 1), expected_start=date(2024, 1, 1), expected_end=date(2024, 1, 31))
        assert_period(date(2024, 4, 1), expected_start=date(2024, 4, 1), expected_end=date(2024, 4, 30))
        assert_period(date(2024, 12, 31), expected_start=date(2024, 12, 1), expected_end=date(2024, 12, 31))
        assert_period(date(2024, 12, 1), expected_start=date(2024, 12, 1), expected_end=date(2024, 12, 31))

        # Complexe start dates
        self.env.company.account_return_periodicity = 'trimester'

        self.basic_return_type.deadline_start_date = '2024-02-06'
        assert_period(date(2024, 2, 5), expected_start=date(2023, 11, 6), expected_end=date(2024, 2, 5))
        assert_period(date(2024, 2, 1), expected_start=date(2023, 11, 6), expected_end=date(2024, 2, 5))
        assert_period(date(2023, 11, 7), expected_start=date(2023, 11, 6), expected_end=date(2024, 2, 5))

        assert_period(date(2024, 2, 6), expected_start=date(2024, 2, 6), expected_end=date(2024, 5, 5))
        assert_period(date(2024, 5, 5), expected_start=date(2024, 2, 6), expected_end=date(2024, 5, 5))
        assert_period(date(2024, 4, 5), expected_start=date(2024, 2, 6), expected_end=date(2024, 5, 5))

        assert_period(date(2024, 5, 6), expected_start=date(2024, 5, 6), expected_end=date(2024, 8, 5))
        assert_period(date(2024, 11, 5), expected_start=date(2024, 8, 6), expected_end=date(2024, 11, 5))
        assert_period(date(2024, 11, 6), expected_start=date(2024, 11, 6), expected_end=date(2025, 2, 5))

        self.basic_return_type.deadline_start_date = '2024-06-06'
        assert_period(date(2024, 3, 5), expected_start=date(2023, 12, 6), expected_end=date(2024, 3, 5))
        assert_period(date(2024, 6, 5), expected_start=date(2024, 3, 6), expected_end=date(2024, 6, 5))
        assert_period(date(2024, 9, 5), expected_start=date(2024, 6, 6), expected_end=date(2024, 9, 5))
        assert_period(date(2024, 12, 5), expected_start=date(2024, 9, 6), expected_end=date(2024, 12, 5))

        self.env.company.account_return_periodicity = 'monthly'
        assert_period(date(2024, 3, 5), expected_start=date(2024, 2, 6), expected_end=date(2024, 3, 5))
        assert_period(date(2024, 3, 6), expected_start=date(2024, 3, 6), expected_end=date(2024, 4, 5))
        assert_period(date(2024, 12, 5), expected_start=date(2024, 11, 6), expected_end=date(2024, 12, 5))
        assert_period(date(2024, 12, 6), expected_start=date(2024, 12, 6), expected_end=date(2025, 1, 5))
        assert_period(date(2025, 1, 5), expected_start=date(2024, 12, 6), expected_end=date(2025, 1, 5))

    def test_vat_closing_moves_with_lock_date(self):
        """ Checks posting a closing entry after the tax lock date has been manually set is allowed.
        """
        self.env.company.tax_lock_date = '2024-12-31'

        first_return = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('date_from', '=', '2024-01-01'),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertEqual(len(first_return), 1)

        first_return.action_review()
        with self.allow_pdf_render():
            first_return.action_submit()

        self.assertTrue(first_return.closing_move_ids)

    def test_multicompany_generation_branches(self):
        with self._patch_returns_generation():
            branch_1_data = self.setup_other_company(name='Branch 1', parent_id=self.company_data['company'].id)
            branch_2_data = self.setup_other_company(name='Branch 2', vat='23434344', parent_id=self.company_data['company'].id, account_return_periodicity='semester', account_opening_date="2014-01-01")
            branch_1_1_data = self.setup_other_company(name='Branch 1-1', parent_id=branch_1_data['company'].id)
            branch_2_1_data = self.setup_other_company(name='Branch 2-1', parent_id=branch_2_data['company'].id)

            vat_tree_1 = self.company_data['company'] + branch_1_data['company'] + branch_1_1_data['company']
            vat_tree_2 = branch_2_data['company'] + branch_2_1_data['company']

            tree_1_returns = self.env['account.return'].search([('type_id', '=', self.basic_return_type.id), ('company_ids', 'in', vat_tree_1.ids)])
            self.assert_return_dates_equal(
                tree_1_returns,
                [
                    ("2024-01-01", "2024-01-31"),
                    ("2024-02-01", "2024-02-29"),
                    ("2024-03-01", "2024-03-31"),
                    ("2024-04-01", "2024-04-30"),
                    ("2024-05-01", "2024-05-31"),
                    ("2024-06-01", "2024-06-30"),
                    ("2024-07-01", "2024-07-31"),
                    ("2024-08-01", "2024-08-31"),
                    ("2024-09-01", "2024-09-30"),
                    ("2024-10-01", "2024-10-31"),
                    ("2024-11-01", "2024-11-30"),
                ],
            )
            self.assertTrue(all(tax_return.company_ids == vat_tree_1 for tax_return in tree_1_returns))

            tree_2_returns = self.env['account.return'].search([('type_id', '=', self.basic_return_type.id), ('company_ids', 'in', vat_tree_2.ids)])
            self.assert_return_dates_equal(
                tree_2_returns,
                [
                    ("2024-01-01", "2024-06-30"),
                ],
            )
            self.assertTrue(all(tax_return.company_ids == vat_tree_2 for tax_return in tree_2_returns))

    def test_multicompany_generation_tax_units(self):
        fiscal_country = self.company_data['company'].account_fiscal_country_id
        self.basic_return_type.report_id.country_id = fiscal_country  # To make sure the tax unit is properly detected
        other_company_data = self.setup_other_company(name="Tax unit other company", account_opening_date='2024-01-01')
        unit_companies = self.company_data['company'] + other_company_data['company']

        with self._patch_returns_generation():
            self.company_data['company'].account_return_periodicity = '2_months'
            other_company_data['company'].account_return_periodicity = 'monthly'

        self.assert_return_dates_equal(
            self.env['account.return'].search([('type_id', '=', self.basic_return_type.id), ('company_ids', 'in', self.company_data['company'].id)]),
            [
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
            ],
        )

        self.assert_return_dates_equal(
            self.env['account.return'].search([('type_id', '=', self.basic_return_type.id), ('company_ids', 'in', other_company_data['company'].id)]),
            [
                ("2024-01-01", "2024-01-31"),
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
                ("2024-04-01", "2024-04-30"),
                ("2024-05-01", "2024-05-31"),
                ("2024-06-01", "2024-06-30"),
                ("2024-07-01", "2024-07-31"),
                ("2024-08-01", "2024-08-31"),
                ("2024-09-01", "2024-09-30"),
                ("2024-10-01", "2024-10-31"),
                ("2024-11-01", "2024-11-30"),
            ],
        )

        with self._patch_returns_generation():
            tax_unit = self.env['account.tax.unit'].create({
                'name': "Tax Unit",
                'country_id': fiscal_country.id,
                'main_company_id': self.company_data['company'].id,
                'company_ids': unit_companies.ids,
                'vat': '6537643',
            })

        unit_returns = self.env['account.return'].search([('type_id', '=', self.basic_return_type.id), ('company_ids', 'in', unit_companies.ids)])

        self.assert_return_dates_equal(
            unit_returns,
            [
                ("2024-01-01", "2024-02-29"),
                ("2024-03-01", "2024-04-30"),
                ("2024-05-01", "2024-06-30"),
                ("2024-07-01", "2024-08-31"),
                ("2024-09-01", "2024-10-31"),
            ],
        )

        self.assertTrue(all(tax_return.company_ids == unit_companies for tax_return in unit_returns))
        self.assertTrue(all(tax_return.tax_unit_id == tax_unit for tax_return in unit_returns))

    def test_cannot_reset_if_subsequent_submitted(self):
        first_return, second_return = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.company_data['company'].id),
        ], order='date_to ASC', limit=2)

        first_return.action_review()
        second_return.action_review()
        with self.allow_pdf_render():
            first_return.action_submit()
            second_return.action_submit()

        with self.assertRaises(UserError):
            first_return.action_reset_to_reviewed()

        second_return.action_reset_to_reviewed()
        first_return.action_reset_to_reviewed()

    def test_cannot_submit_if_previous_not_submitted(self):
        first_return, second_return = self.env['account.return'].search([
            ('type_id', '=', self.basic_return_type.id),
            ('company_id', '=', self.company_data['company'].id),
        ], order='date_to ASC', limit=2)

        second_return.action_review()
        with self.allow_pdf_render():
            with self.assertRaises(UserError):
                second_return.action_submit()

        first_return.action_review()
        with self.allow_pdf_render():
            first_return.action_submit()
            second_return.action_submit()

    def test_return_manual_creation_wizard_single_return(self):
        original_number_of_returns = self.env['account.return'].search_count([])
        wizard = self.env['account.return.creation.wizard'].create([{
            'date_from': '2023-12-01',
            'date_to': '2023-12-31',
            'return_type_id': self.basic_return_type.id,
        }])
        wizard.action_create_manual_account_returns()
        new_number_of_returns = self.env['account.return'].search_count([])

        self.assertEqual(new_number_of_returns, original_number_of_returns + 1)

        new_return = self.env['account.return'].search([], order='date_from')[0]
        self.assertRecordValues(
            new_return,
            [{
                'company_id': self.env.company.id,
                'type_id': self.basic_return_type.id,
            }]
        )
        self.assert_return_dates_equal(
            new_return,
            [("2023-12-01", "2023-12-31")]
        )

    def test_return_manual_creation_wizard_multiple_returns(self):
        original_number_of_returns = self.env['account.return'].search_count([])
        wizard = self.env['account.return.creation.wizard'].create([{
            'date_from': '2023-10-01',
            'date_to': '2023-12-31',
            'return_type_id': self.basic_return_type.id,
        }])
        wizard.action_create_manual_account_returns()

        new_number_of_returns = self.env['account.return'].search_count([])
        self.assertEqual(new_number_of_returns, original_number_of_returns + 3)

        new_returns = self.env['account.return'].search([], order='date_from')[:3]
        self.assertEqual(new_returns.company_id.id, self.env.company.id)
        self.assertEqual(new_returns.type_id.id, self.basic_return_type.id)
        self.assert_return_dates_equal(
            new_returns,
            [
                ("2023-10-01", "2023-10-31"),
                ("2023-11-01", "2023-11-30"),
                ("2023-12-01", "2023-12-31"),
            ]
        )

    def test_return_manual_creation_wizard_wrong_dates(self):
        wizard = self.env['account.return.creation.wizard'].create([{
            'date_from': '2023-10-15',
            'date_to': '2023-12-31',
            'return_type_id': self.basic_return_type.id,
        }])
        self.assertEqual(wizard.show_warning_wrong_dates, True)
        wizard.write({
            'date_from': '2023-12-01',
        })
        self.assertEqual(wizard.show_warning_wrong_dates, False)

    def test_return_manual_creation_wizard_warning_existing_return(self):
        wizard = self.env['account.return.creation.wizard'].create([{
            'date_from': '2023-12-01',
            'date_to': '2023-12-31',
            'return_type_id': self.basic_return_type.id,
        }])

        self.assertEqual(wizard.show_warning_existing_return, False)
        wizard.action_create_manual_account_returns()

        new_wizard = self.env['account.return.creation.wizard'].create([{
            'date_from': '2023-12-01',
            'date_to': '2023-12-31',
            'return_type_id': self.basic_return_type.id,
        }])
        self.assertEqual(new_wizard.show_warning_existing_return, True)

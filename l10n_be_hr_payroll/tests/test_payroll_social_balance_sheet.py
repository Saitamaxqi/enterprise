from datetime import date

from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayrollSocialBalanceSheet(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.journal = cls.env['account.journal'].create({
            'name': 'Salary Journal - Test',
            'code': 'SLR',
            'type': 'general',
            'company_id': cls.belgian_company.id,
        })

        cls.cp200_salary_structure = cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary')
        cls.cp200_salary_structure.journal_id = cls.journal.id

        cls.date_from = date(2024, 1, 1)
        cls.date_to = date(2024, 1, 31)

        test_employees = (
            cls.employee_georges |
            cls.employee_john |
            cls.employee_a |
            cls.employee_test |
            cls.employee_with_attestation |
            cls.employee_withholding_taxes
        )
        for emp in test_employees:
            if emp == cls.employee_test or emp == cls.employee_withholding_taxes:
                emp.certificate = 'other'
            else:
                emp.certificate = 'bachelor'

        for version in test_employees.version_id:
            if version.employee_id == cls.employee_a or version.employee_id == cls.employee_test:
                version.sex = 'female'
            else:
                version.sex = 'male'
        versions = test_employees._get_versions_with_contract_overlap_with_period(cls.date_from, cls.date_to)

        # Generate and confirm payslips
        payslips = cls.env['hr.payslip'].create([{
            'name': f'Payslip - {version.employee_id.name} - 1/2024',
            'employee_id': version.employee_id.id,
            'version_id': version.id,
            'struct_id': cls.cp200_salary_structure.id,
            'date_from': cls.date_from,
            'date_to': cls.date_to,
        } for version in versions])

        payslips.compute_sheet()
        payslips.action_payslip_done()

    def test_social_balance_report_generation(self):
        """
        Tests Social Balance Sheet PDF report generation.
        """
        social_balance_wizard = self.env['l10n.be.social.balance.sheet'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.belgian_company.id,
        })
        social_balance_wizard.print_report()

        self.assertTrue(
            social_balance_wizard.social_balance_sheet,
            "The PDF report should generate a file."
        )
        self.assertEqual(
            social_balance_wizard.state, 'done',
            "The state should be 'done' after generating the PDF report."
        )

    def test_social_balance_xlsx_export(self):
        """
        Tests Social Balance Sheet XLSX exports.
        """
        test_employees = (
            self.employee_georges |
            self.employee_john |
            self.employee_a |
            self.employee_test |
            self.employee_with_attestation |
            self.employee_withholding_taxes
        )
        for emp in test_employees:
            if not emp.certificate:
                emp.certificate = 'other'

        for version in test_employees.version_id:
            if version.employee_id == self.employee_a or version.employee_id == self.employee_test:
                version.sex = 'female'
            else:
                version.sex = 'male'
        self.employee_test.certificate = 'other'
        social_balance_wizard = self.env['l10n.be.social.balance.sheet'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.belgian_company.id,
        })

        social_balance_wizard.export_report_xlsx()

        self.assertTrue(
            social_balance_wizard.social_balance_xlsx,
            "The XLSX export should generate a file."
        )
        self.assertEqual(
            social_balance_wizard.state_xlsx, 'done',
            "The XLSX state should be 'done' after generating the report."
        )

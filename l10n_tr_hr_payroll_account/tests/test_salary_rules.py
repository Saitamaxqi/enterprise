# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('tr')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.tr'),
            structure=cls.env.ref('l10n_tr_hr_payroll.hr_payroll_structure_tr_employee_salary'),
            structure_type=cls.env.ref('l10n_tr_hr_payroll.structure_type_employee_tr'),
            contract_fields={
                'wage': 50000,
            }
        )

    def test_basic_payslip(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {
            "BASIC": 50000.0,
            "SSIEDED": -7000.0,
            "SSIDED": -500.0,
            "SSICDED": 7750.0,
            "SSIUCDED": 1000.0,
            "GROSS": 42500.0,
            "TAXB": 42500.0,
            "TOTTB": 6375.0,
            "ACTD": 0.0,
            "BTAXNET": 6375.0,
            "BTNET": -3824.68,
            "STAX": -227.68,
            "NETTAX": -4052.36,
            "NET": 38447.64,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip_second_month = self._generate_payslip(date(2024, 2, 1), date(2024, 2, 29))
        payslip_second_month_results = {
            "BASIC": 50000.0,
            "SSIEDED": -7000.0,
            "SSIDED": -500.0,
            "SSICDED": 7750.0,
            "SSIUCDED": 1000.0,
            "GROSS": 42500.0,
            "TAXB": 85000.0,
            "TOTTB": 12750.0,
            "ACTD": 6375.0,
            "BTAXNET": 6375.0,
            "BTNET": -3824.68,
            "STAX": -227.68,
            "NETTAX": -4052.36,
            "NET": 38447.64,
        }
        self._validate_payslip(payslip_second_month, payslip_second_month_results)
        payslip_second_month.action_payslip_done()
        payslip_second_month.action_payslip_paid()

        payslip_third_month = self._generate_payslip(date(2024, 3, 1), date(2024, 3, 31))
        payslip_third_month_results = {
            "BASIC": 50000.0,
            "SSIEDED": -7000.0,
            "SSIDED": -500.0,
            "SSICDED": 7750.0,
            "SSIUCDED": 1000.0,
            "GROSS": 42500.0,
            "TAXB": 127500.0,
            "TOTTB": 20000.0,
            "ACTD": 12750.0,
            "BTAXNET": 7250.0,
            "BTNET": -4699.68,
            "STAX": -227.68,
            "NETTAX": -4927.36,
            "NET": 37572.64,
        }

        payslip_second_month.action_payslip_cancel()
        payslip_third_month.compute_sheet()
        payslip_third_month_results = payslip_second_month_results
        self._validate_payslip(payslip_third_month, payslip_third_month_results)

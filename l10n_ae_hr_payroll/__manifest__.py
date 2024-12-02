# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'U.A.E. - Payroll',
    'countries': ['ae'],
    'author': 'Odoo PS',
    'category': 'Human Resources/Payroll',
    'description': """
United Arab Emirates Payroll and End of Service rules.
=======================================================

    """,
    'depends': ['hr_payroll', 'hr_work_entry_holidays'],
    'auto_install': ['hr_payroll'],
    'data': [
        'views/hr_payroll_report.xml',
        'views/report_payslip_templates.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_leave_type_views.xml',
        'views/res_bank_views.xml',
        'views/res_config_settings_view.xml',
        'wizard/hr_payroll_payment_report_wizard.xml',
    ],
    'demo': [
        'data/l10n_ae_hr_payroll_demo.xml'
    ],
    'license': 'OEEL-1',
}

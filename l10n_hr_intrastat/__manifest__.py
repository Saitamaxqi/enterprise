{
    'name': 'Croatian Intrastat Declaration',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Generates Intrastat PDF report for declaration based on invoices.
    """,
    'depends': ['account_intrastat', 'l10n_hr_reports'],
    'data': [
        'data/account_return_data.xml',
        'security/ir.model.access.csv',
        'views/account_return_views.xml',
        'wizard/intrastat_goods_submission_wizard.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

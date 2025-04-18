{
    'name': 'Belgium - Accounting Reports - Prorata Deduction',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
        Provides the option to add the prorata deduction to the VAT export
    """,
    'depends': [
        'l10n_be_reports'
    ],
    'data': [
        'wizard/vat_report_export.xml',
        'data/prorata_template.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/page/accounting',
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

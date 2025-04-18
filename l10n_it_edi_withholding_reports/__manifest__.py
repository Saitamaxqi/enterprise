{
    'name': 'Italy EDI Witholding - Accounting Reports',
    'version': '1.0',
    'description': """
Accounting reports for Italy
============================

    """,
    'category': 'Accounting/Accounting',
    'depends': ['l10n_it_edi_withholding', 'account_reports'],
    'data': [
        'data/account_return_data.xml',
    ],
    'auto_install': ['l10n_it_edi_withholding', 'account_reports'],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

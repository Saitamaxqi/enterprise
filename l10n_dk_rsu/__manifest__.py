{
    'name': 'Danish - RSU',
    'version': '1.0',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations/SBR',
    'summary': 'Danish Localization - RSU',
    'description': """
RSU Danish Localization.
========================
Submit your Tax Reports to the Danish tax authorities
    """,
    'depends': ['l10n_dk_reports'],
    'data': [
        'data/tax_report.xml',
        'wizard/tax_report_wizard.xml',
        'security/ir.model.access.csv',
        'views/template_rsu.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}

{
    'name': 'ESG HR Fleet',
    'version': '1.0',
    'summary': "Measure fleet emissions based on your employees' commuting distance and vehicle data.",
    'depends': [
        'esg',
        'hr_fleet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/esg_employee_commuting_report_views.xml',
        'views/esg_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

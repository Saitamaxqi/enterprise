{
    'name': 'ESG HR Contract',
    'version': '1.0',
    'summary': "Use your employee's contracts data to measure important ESG metrics (e.g. pay gap, contract types).",
    'depends': [
        'esg_hr',
        'hr_contract',
    ],
    'data': [
        'report/esg_employee_report_views.xml',
        'views/esg_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'esg_hr_contract/static/src/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

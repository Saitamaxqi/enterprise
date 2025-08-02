{
    'name': 'Audit Reports',
    'summary': 'Create Audit Reports with Knowledge',
    'version': '1.0',
    'depends': [
        'accountant',
        'knowledge',
        'sign',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/reports.xml',
        'views/audit_report_views.xml',
        'views/knowledge_article_views.xml',
        'views/menuitems.xml',
        'data/ir_actions_report_data.xml',
        'data/ir_attachment_data.xml',
        'data/knowledge_article_template_category_data.xml',
        'data/knowledge_article_template_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'accountant_knowledge/static/src/components/**/*',
            'accountant_knowledge/static/src/editor/**/*',
            'accountant_knowledge/static/src/scss/**/*',
            'accountant_knowledge/static/src/views/**/*',
        ],
        'web.assets_frontend': [
            'accountant_knowledge/static/src/editor/embedded_components/core/**/*',
            'accountant_knowledge/static/src/public/**/*',
        ]
    },
}

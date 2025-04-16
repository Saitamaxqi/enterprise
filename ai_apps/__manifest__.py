# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'AI',
    'version': '0.1',
    'sequence': 420,
    'summary': 'Artificial Intelligence Text Drafting Feature Management',
    'depends': [
        'base',
        'base_setup',
        'mail',
        'web',
    ],
    'data': [
        'security/ai_app_security.xml',
        'security/ir.model.access.csv',
        'data/ai_composer_data.xml',
        'views/ai_composer_views.xml',
        'views/ai_app_menu.xml',
        'views/mail_scheduled_message_views.xml',
        'wizard/mail_compose_message_views.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'ai_apps/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

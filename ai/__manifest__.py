# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'AI',
    'version': '1.0',
    'category': 'Hidden',
    'summary': """
        A powerful suite of AI tools and agents
        integrated directly into your Odoo environment.""",
    'description': """
        * Create and manage AI agents for various business tasks
        * Integrate with popular AI models and services
        * Process documents and extract information automatically
        * Enhance customer service with AI-powered responses
        * Automate routine tasks with intelligent workflows
    """,
    'depends': ['mail', 'attachment_indexation'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_agent_views.xml',
        'views/ai_topic_views.xml',
        'views/res_config_settings_views.xml',
        'views/ai_composer_views.xml',
        'views/ai_menus.xml',
        'views/mail_scheduled_message_views.xml',
        'views/mail_template_views.xml',
        'data/ir_cron.xml',
        'data/ai_composer_data.xml',
        'wizard/mail_compose_message_views.xml',
    ],
    'demo': [
        'data/ai_agent_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'ai/static/tests/**/*',
        ],
    },
    'pre_init_hook': "_pre_init_ai",
    'application': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

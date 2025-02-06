# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'AI Calendar',
    'version': '1.0',
    'category': 'AI',
    'summary': """
        Enhance AI functionality by leveraging Calendar actions.
        """,
    'depends': ['ai', 'calendar'],
    'data': [
        'views/action_views.xml',
        'data/ai_tool_data.xml',
        'data/ai_topic_data.xml',
    ],
    'demo': [
        'data/ai_agent_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

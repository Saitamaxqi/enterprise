# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "VoIP Recording & Transcription",
    "depends": ["voip", "ai"],
    'auto_install': True,
    'category': 'Hidden',
    'summary': "Extend VoIP with AI features (such as transcription)",
    'version': '1.0',
    'data': [
        'views/voip_call_views.xml',
        'views/voip_provider_views.xml',
        'data/ir_cron.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "ai_voip/static/src/**/*",
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

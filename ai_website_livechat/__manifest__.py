{
    'name': "AI Website Livechat Integration",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "AI website livechat components for web builder",
    'depends': ['ai', 'website', 'im_livechat', 'html_builder'],
    'data': [
        'data/ir_cron_data.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_ai_livechat.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_website_livechat/static/src/discuss/core/web/**/*',
        ],
        'im_livechat.assets_embed_core': [
            'ai_website_livechat/static/src/discuss/core/common/**/*',
        ],
        'web.assets_frontend': [
            'web/static/lib/dompurify/DOMpurify.js',
            'ai_website_livechat/static/src/website/components/**/*',
            'ai_website_livechat/static/src/website/interactions/*',
        ],
        'website.assets_edit_frontend': [
            'ai_website_livechat/static/src/website/interactions/edit/**/*',
        ],
        'html_builder.assets': [
            'ai_website_livechat/static/src/website/plugins/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

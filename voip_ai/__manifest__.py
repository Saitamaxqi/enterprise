{  # noqa: B018
    "name": "Phone - AI",
    "depends": ["voip", "ai"],
    "auto_install": True,
    "category": "Productivity/Phone",
    "summary": "Extend Phone with AI features (such as transcription)",
    "version": "1.0",
    "data": [
        "views/voip_call_views.xml",
        "views/voip_provider_views.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "voip_ai/static/src/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "OEEL-1",
}

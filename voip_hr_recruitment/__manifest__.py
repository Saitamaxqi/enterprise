{
    "name": "VoIP Integration for Recruitment",
    "version": "1.0",
    "category": "Human Resources/Recruitment",
    "depends": ["hr_recruitment", "voip"],
    "auto_install": True,
    "license": "OEEL-1",
    "data": [
        "views/voip_call_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "voip_hr_recruitment/static/src/**/*",
        ],
    },
    "author": "Odoo S.A.",
}

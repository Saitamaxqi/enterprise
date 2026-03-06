{
    'name': 'Administration Asset Management',
    'version': '1.0',
    'summary': 'Administrative Asset Tracking',
    'category': 'Administration',
    'author': 'Open-Inside',
    'depends': ['account_asset', 'hr'],
    'data': [
        'security/asset_move_history_security.xml',
        'security/ir.model.access.csv',
        'views/asset_views.xml',
        'views/asset_location_views.xml',
        'views/asset_move_history_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
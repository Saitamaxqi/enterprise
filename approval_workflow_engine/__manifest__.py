{
    'name': 'Approval Workflow Engine',
    'version': '1.0',
    'summary': 'Approval Workflow Engine',
    'category': 'Administration',
    'author': 'Open-Inside',
    'depends': ['base', 'mail'],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/approval_sequence.xml',

        # Views
        'views/approval_log_views.xml',
        'views/approval_request_views.xml',
        'views/approval_stage_views.xml',
        'views/approval_workflow_views.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'application': True,
}

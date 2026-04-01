{
    'name': 'Approval Workflow Engine',
    'version': '1.0',
    'summary': 'Approval Workflow Engine',
    'category': 'Administration',
    'author': 'Open-Inside',
    'depends': ['base', 'mail'],
    'data': [
        
        'security/ir.model.access.csv',
        'data/approval_sequence.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
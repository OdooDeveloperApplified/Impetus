{
    'name': 'Impel CRM',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified Purchase',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','crm','web'],
    'data': [
        'security/ir.model.access.csv',
        
        'views/crm_lead_view.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'license':'LGPL-3',
}
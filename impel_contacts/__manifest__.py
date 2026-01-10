{
    'name': 'Impel Contacts',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified contacts',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','contacts'],
    'data': [
        'security/ir.model.access.csv',
     
        'views/contacts_template_views.xml',
        'views/group_name_views.xml',
       
    ],
    
    'assets': {},
    'installable': True,
    'auto_install': False,
    'license':'LGPL-3',
}
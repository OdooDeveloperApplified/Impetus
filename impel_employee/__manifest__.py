{
    'name': 'Impel Employee',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified contacts',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/appraisal_card_data.xml',
        'views/employee_template_views.xml',
        'views/appraisal_card_view.xml',
        'views/appraisal_line_view.xml',
    ],
    
    'assets': {},
    'installable': True,
    'auto_install': False,
    'license':'LGPL-3',
}
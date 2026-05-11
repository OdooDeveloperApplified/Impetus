{
    'name': 'Impel Sales',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified Sales',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','sale','web','sale_stock','stock','account','account_accountant','hr'],
    'data': [
        'security/ir.model.access.csv',
        
        'views/sale_template_views.xml',
        'views/pf_charges_wizard_view.xml',
        'reports/custom_report.xml',
        'reports/saleorder_report.xml',
        'reports/so_odoodefault_report.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'license':'LGPL-3',
}
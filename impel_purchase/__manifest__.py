{
    'name': 'Impel Purchase',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified Purchase',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','purchase','web'],
    'data': [
        'security/ir.model.access.csv',
        
        'views/purchase_order_view.xml',
        'reports/custom_purchase_order_report.xml',
        'reports/purchase_indent_report.xml',
        'reports/po_odoodefault_report.xml',
        'reports/rfq_odoodefault_report.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
}
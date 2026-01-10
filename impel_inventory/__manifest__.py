{
    'name': 'Impel Inventory',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified Inventory',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','sale','web','stock'],
    'data': [
        # 'security/ir.model.access.csv',
        'reports/delivery_challan_report.xml',
        'reports/receipt_incoming_mat.xml',
        'reports/receipt_default_report.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
}
{
    'name': 'Impel Invoice',
    'version': '17.0.1.0',
    'category': 'HR',
    'author': 'Applified Sales',
    'website': 'https://www.impel.com',
    'depends': ['base', 'mail','sale','web','purchase', 'account','sale_management','impel_sales'],
    'data': [
        "reports/tax_invoice_report.xml",
        "reports/credit_note_report.xml",
        "reports/receipt.xml",
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
}
from odoo import models, fields, api
from num2words import num2words
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    transport = fields.Char(string="Transport", compute="_compute_transport", store=True)
    way_bill_no = fields.Char(string="E-Way Bill No.", compute="_compute_transport", store=True)
    po_number = fields.Char(string="PO Number", compute="_compute_transport", store=True)
    po_date = fields.Date(string="PO Date", compute="_compute_transport", store=True)
    discount_percentage = fields.Float(string="Discount Percentage")

    @api.depends('invoice_origin')
    def _compute_transport(self):
        for move in self:
            sale = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            move.transport = getattr(sale, 'transport', False)
            move.way_bill_no = getattr(sale, 'way_bill_no', False)
            move.po_number = getattr(sale, 'po_number', False)
            move.po_date = getattr(sale, 'po_date', False)
            move.discount_percentage = sale.discount_percentage or 0.0

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def amount_to_text_indian(self, amount):
        """
        Converts a numeric amount into Indian currency words.
        Example: 123456.78 -> 'Twelve Lakh Thirty Four Thousand Four Hundred Fifty Six Rupees and Seventy Eight Paise'
        """
        if not amount:
            return ''

        try:
            amount = float(amount)
        except Exception:
            return ''

        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))

        rupees_words = num2words(rupees, lang='en_IN').title()
        if paise > 0:
            paise_words = num2words(paise, lang='en_IN').title()
            return f"{rupees_words} Rupees And {paise_words} Paise"

        return f"{rupees_words} Rupees"
    

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # stored field so wizard can write directly
    discount_percentage = fields.Float(string="Discount Percentage", digits=(12, 6))

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_percentage': self.discount_percentage or 0.0,
        })
        return invoice_vals
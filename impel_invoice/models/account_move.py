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
    custom_salesperson = fields.Many2one('hr.employee', string='Salesperson (Employee)', required=True, tracking=True)
    is_from_sale_order = fields.Boolean(
        string="From Sale Order",
        compute="_compute_is_from_sale_order",
        store=True
    )

    @api.depends('invoice_line_ids.sale_line_ids')
    def _compute_is_from_sale_order(self):
        for move in self:
            move.is_from_sale_order = any(
                line.sale_line_ids for line in move.invoice_line_ids
            )

    @api.depends('invoice_origin')
    def _compute_transport(self):
        for move in self:
            sale = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            move.transport = getattr(sale, 'transport', False)
            move.way_bill_no = getattr(sale, 'way_bill_no', False)
            move.po_number = getattr(sale, 'po_number', False)
            move.po_date = getattr(sale, 'po_date', False)
            move.discount_percentage = sale.discount_percentage or 0.0
    
    def _get_financial_year(self, date):
        """
        Returns financial year like 26-27
        FY in India: April → March
        """
        if not date:
            date = fields.Date.today()

        year = date.year

        if date.month >= 4:
            start_year = year
            end_year = year + 1
        else:
            start_year = year - 1
            end_year = year

        return f"{str(start_year)[-2:]}-{str(end_year)[-2:]}"
    
    def _get_branch_sequence(self):
        self.ensure_one()

        if not self.company_id:
            return False

        code_map = {
            'out_invoice': ('company.invoice', 'INV'),
            'in_invoice': ('company.bill', 'BILL'),
            'out_refund': ('company.customer.refund', 'CRN'),
            'in_refund': ('company.vendor.refund', 'VRN'),
        }

        seq_data = code_map.get(self.move_type)
        if not seq_data:
            return False

        seq_code = seq_data

        # financial year
        fy = self._get_financial_year(self.invoice_date or fields.Date.today())

        # VERY IMPORTANT → include FY in sequence_code
        sequence_code = f"{seq_code}.{self.company_id.id}.{fy}"

        sequence = self.env['ir.sequence'].search([
            ('code', '=', sequence_code),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not sequence:
            branch = self.company_id.branch_code or self.company_id.name or 'COMP'

            sequence = self.env['ir.sequence'].create({
                'name': f"{branch} {fy}",
                'code': sequence_code,
                'prefix': f"{branch}-{fy}-",
                'padding': 5,
                'implementation': 'no_gap',
                'company_id': self.company_id.id,
            })

        return sequence
    
    def action_post(self):
        for move in self:
            if move.name == '/' and move.company_id:
                sequence = move._get_branch_sequence()
                if sequence:
                    move.name = sequence.next_by_id()

        return super(AccountMove, self).action_post()

class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_code = fields.Char(string="Branch Code")

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
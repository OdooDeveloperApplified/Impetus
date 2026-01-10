from odoo import api, fields, models
import logging
import math

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    indent_no = fields.Char(string="Indent No.")
    executive = fields.Char(string="Executive")
    mc_details = fields.Char(string="MC Details")
    service_report_no = fields.Char(string="Service Report No.")
    gr_no = fields.Char(string="GR/RR No.")
    transport = fields.Char(string="Transport")
    vehicle_no = fields.Char(string="Vehicle No.")
    e_way_bill_no = fields.Char(string="E-Way Bill No.")

    is_enabled_roundoff = fields.Boolean(string="Apply Roundoff", default=True)
    amount_roundoff = fields.Monetary(string='Amount (Rounded)', compute='_compute_amount_roundoff', store=True)
    amount_total_rounded = fields.Monetary(string='Total (Rounded)', compute='_compute_amount_roundoff', store=True)

    @api.depends('amount_total', 'is_enabled_roundoff')
    def _compute_amount_roundoff(self):
        for order in self:
            if order.is_enabled_roundoff:
                # Normal rounding: 23.50 → 24, 23.30 → 23
                rounded_total = round(order.amount_total)

                order.amount_total_rounded = rounded_total
                order.amount_roundoff = rounded_total - order.amount_total
            else:
                order.amount_total_rounded = order.amount_total
                order.amount_roundoff = 0.0

class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def amount_to_text_indian(self, amount):
        """
        Convert a number to Indian-style words (e.g., 'One Lakh Twenty Three Thousand').
        """
        # Use Odoo’s built-in function as base
        amount_text = self.amount_to_text(amount)
        # You can customize the wording if needed
        return amount_text.replace("Hundred Thousand", "Lakh").replace("Million", "Crore")
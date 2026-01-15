from odoo import api, fields, models
from num2words import num2words

class StockPicking(models.Model):
    _inherit = "stock.picking"

    gr_no = fields.Char(string="GR/RR No.")
    transport = fields.Char(string="Transport")
    vehicle_no = fields.Char(string="Vehicle No.")
    po_number = fields.Char(string="PO Number")
    po_date = fields.Date(string="PO Date")
    transport_type = fields.Char(string="Transport Type")
    way_bill_no = fields.Char(string="E-Way Bill No.")

    @api.model
    def create(self, vals):
        """Auto-fill delivery fields from sale order"""
        picking = super().create(vals)
        if picking.origin:
            sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
            if sale_order:
                picking.gr_no = sale_order.gr_no
                picking.transport = sale_order.transport
                picking.vehicle_no = sale_order.vehicle_no
                picking.po_number = sale_order.po_number
                picking.po_date = sale_order.po_date
                picking.transport_type = sale_order.transport_type
                picking.way_bill_no = sale_order.way_bill_no
        return picking
    
    @api.model
    def get_hsn_summary(self):
        summary = {}

        for move in self.move_ids_without_package:
            purchase_line = move.purchase_line_id
            sale_line = move.sale_line_id
            line = purchase_line or sale_line
            if not line:
                continue

            product = move.product_id
            hsn = product.l10n_in_hsn_code or 'N/A'
            uom = move.product_uom.name or ''

            qty = move.quantity or 0.0
            price_unit = line.price_unit or 0.0
            discount = line.discount or 0.0
            price_after_discount = price_unit * (1 - discount / 100.0)

            taxes = purchase_line.taxes_id if purchase_line else sale_line.tax_id
            currency = (
                self.purchase_id.currency_id
                if self.purchase_id
                else self.company_id.currency_id
            )

            tax_data = taxes.compute_all(
                price_after_discount,
                currency=currency,
                quantity=qty,
                product=product,
                partner=self.partner_id,
            )

            taxable_amount = tax_data['total_excluded']
            cgst = sgst = igst = 0.0
            tax_rate = 0.0

            for t in tax_data['taxes']:
                tax = self.env['account.tax'].browse(t['id'])
                tax_rate += tax.amount

                name = (t.get('name') or '').upper()
                if 'CGST' in name:
                    cgst += t['amount']
                elif 'SGST' in name:
                    sgst += t['amount']
                elif 'IGST' in name:
                    igst += t['amount']

            if hsn not in summary:
                summary[hsn] = {
                    'qty': 0.0,
                    'uom': uom,
                    'amount': 0.0,
                    'tax_rate': tax_rate,
                    'cgst': 0.0,
                    'sgst': 0.0,
                    'igst': 0.0,
                }

            summary[hsn]['qty'] += qty
            summary[hsn]['amount'] += taxable_amount
            summary[hsn]['cgst'] += cgst
            summary[hsn]['sgst'] += sgst
            summary[hsn]['igst'] += igst

        return summary




class InwardReceiptReport(models.AbstractModel):
    _name = 'report.impel_inventory.inward_receipt_report_views'
    _description = 'Inward Receipt Report'

    @api.model
    def _get_hsn_summary(self, picking):
        summary = {}
        for move in picking.move_ids_without_package:
            po_line = move.purchase_line_id
            if not po_line:
                continue
            hsn = po_line.product_id.l10n_in_hsn_code or 'N/A'
            uom = po_line.product_uom.name or ''
            qty = po_line.product_qty or 0.0
            amount = po_line.price_subtotal or 0.0
            taxes = po_line.taxes_id.mapped('amount')
            tax_rate = ', '.join([str(int(t)) + '%' for t in taxes]) if taxes else '0%'

            if hsn not in summary:
                summary[hsn] = {
                    'qty': 0,
                    'uom': uom,
                    'amount': 0.0,
                    'tax_rate': tax_rate,
                }

            summary[hsn]['qty'] += qty
            summary[hsn]['amount'] += amount
        return summary

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.picking'].browse(docids)
        return {
            'docs': docs,
            'get_hsn_summary': self._get_hsn_summary,
        }

class OutwardDeliveryReport(models.AbstractModel):
    _name = 'report.impel_inventory.delivery_challan_report_views'
    _description = 'Outward Delivery Report'

    @api.model
    def _get_hsn_summary(self, picking):
        summary = {}
        total_amount = 0.0  # for proportional P&F distribution

        for move in picking.move_ids_without_package:
            so_line = move.sale_line_id
            if not so_line:
                continue

            hsn = move.product_id.l10n_in_hsn_code or 'N/A'
            uom = move.product_uom.name or ''
            qty = move.quantity or 0.0
            price_unit = so_line.price_unit or 0.0
            discount = so_line.discount or 0.0

            # Taxable Amount (after discount)
            amount = price_unit * qty * (1 - (discount / 100.0))
            total_amount += amount

            taxes = so_line.tax_id
            total_tax_rate = sum(t.amount for t in taxes)
            igst_amt = (amount * total_tax_rate) / 100 if total_tax_rate else 0.0

            if hsn not in summary:
                summary[hsn] = {
                    'qty': 0.0,
                    'uom': uom,
                    'amount': 0.0,
                    'tax_rate': f"{int(total_tax_rate)}%",
                    'igst_amt': 0.0,
                    'total_tax': 0.0,
                    'final_total': 0.0,
                }

            summary[hsn]['qty'] += qty
            summary[hsn]['amount'] += amount
            summary[hsn]['igst_amt'] += igst_amt
            summary[hsn]['total_tax'] += igst_amt
            summary[hsn]['final_total'] = summary[hsn]['amount'] + summary[hsn]['total_tax']

        # ----------------------------
        # Fetch P&F from Sale Order
        # ----------------------------
        sale_order = picking.sale_id or self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
        pf_total = 0.0
        if sale_order and sale_order.amount_pf:
            pf_total = sale_order.amount_pf

        # ----------------------------
        # Distribute P&F proportionally by taxable amount
        # ----------------------------
        if pf_total > 0 and total_amount > 0:
            for hsn, vals in summary.items():
                proportion = vals['amount'] / total_amount
                pf_share = pf_total * proportion
                vals['amount'] += pf_share

                # Recalculate IGST and totals with added P&F
                tax_rate_value = float(vals['tax_rate'].replace('%', '') or 0.0)
                igst_amt_pf = (pf_share * tax_rate_value) / 100.0
                vals['igst_amt'] += igst_amt_pf
                vals['total_tax'] += igst_amt_pf
                vals['final_total'] = vals['amount'] + vals['total_tax']

        return summary

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.picking'].browse(docids)
        return {
            'docs': docs,
            'get_hsn_summary': self._get_hsn_summary,
        }



   



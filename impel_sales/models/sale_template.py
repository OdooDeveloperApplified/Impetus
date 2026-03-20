from odoo import api, fields, models, _
from num2words import num2words
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import formatLang

class SaleOrder(models.Model):
    _inherit = "sale.order"

    pf_percentage = fields.Float(string="P&F Percentage (%)", default=0.0)
    amount_pf = fields.Monetary(string="P&F Charges", compute="_compute_amounts", store=True)
    amount_total_with_pf = fields.Monetary(string="Grand Total (Incl. P&F)", compute="_compute_amounts", store=True)
    amount_untaxed_with_pf = fields.Monetary(string="Untaxed (Incl. P&F)", compute="_compute_amounts", store=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        compute='_compute_warehouse_id', store=True, readonly=False, precompute=True,
        check_company=True)

    # -------------------------------
    # MAIN COMPUTATION
    # -------------------------------
    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total', 'pf_percentage', 'is_enabled_roundoff')
    def _compute_amounts(self):
        """Compute totals including P&F in Untaxed and apply tax on PF-inclusive base."""
        for order in self:
            order = order.with_company(order.company_id)
            lines = order.order_line.filtered(lambda x: not x.display_type)

            # Base values
            amount_untaxed = sum(lines.mapped('price_subtotal'))
            amount_tax = sum(lines.mapped('price_tax'))

            # PF computation
            pf_value = order.pf_percentage or 0.0
            calc_value = pf_value * 100 if pf_value < 1 else pf_value
            amount_pf = amount_untaxed * (calc_value / 100.0)

            # Untaxed with PF
            amount_untaxed_with_pf = amount_untaxed + amount_pf

            # Recalculate taxes proportionally on PF
            tax_rate = amount_tax / amount_untaxed if amount_untaxed else 0.0
            amount_tax_with_pf = amount_tax + (amount_pf * tax_rate)

            # Final total
            amount_total = amount_untaxed_with_pf + amount_tax_with_pf

            # Handle roundoff
            if order.is_enabled_roundoff:
                rounded_total = round(amount_total)
                amount_roundoff = rounded_total - amount_total
                amount_total_rounded = rounded_total
            else:
                amount_roundoff = 0.0
                amount_total_rounded = amount_total

            # Assign computed values
            order.amount_pf = amount_pf
            order.amount_untaxed_with_pf = amount_untaxed_with_pf
            order.amount_untaxed = amount_untaxed_with_pf   # override displayed Untaxed
            order.amount_tax = amount_tax_with_pf
            order.amount_total = amount_total
            order.amount_total_with_pf = amount_total
            order.amount_roundoff = amount_roundoff
            order.amount_total_rounded = amount_total_rounded

            # Update tax_totals structure for UI
            if order.tax_totals:
                tax_totals = order.tax_totals
                currency = order.currency_id
                group_name = _('Untaxed Amount')

                tax_totals['amount_untaxed'] = amount_untaxed_with_pf
                tax_totals['amount_total'] = amount_total
                tax_totals['subtotals'] = [{
                    'name': group_name,
                    'amount': amount_untaxed_with_pf,
                    'formatted_amount': formatLang(self.env, amount_untaxed_with_pf, currency_obj=currency),
                }]
                first_line = lines[:1]
                if first_line and first_line.tax_id:
                    real_tax_name = first_line.tax_id[0].tax_group_id.name
                else:
                    real_tax_name = _('Taxes')
                tax_totals['groups_by_subtotal'] = {
                    group_name: [{
                        'tax_group_name': real_tax_name,
                        'tax_group_amount': amount_tax_with_pf,
                        'tax_group_base_amount': amount_untaxed_with_pf,
                        'formatted_tax_group_amount': formatLang(self.env, amount_tax_with_pf, currency_obj=currency),
                        'formatted_tax_group_base_amount': formatLang(self.env, amount_untaxed_with_pf, currency_obj=currency),
                        'tax_group_id': 1,
                        'group_key': 1,
                        'hide_base_amount': False,
                    }]
                }
                tax_totals['formatted_amount_total'] = formatLang(self.env, amount_total, currency_obj=currency)
                tax_totals['subtotals_order'] = [group_name]
                order.tax_totals = tax_totals

    # -------------------------------
    # EXTERNAL TAX HANDLING
    # -------------------------------
    def _compute_tax_totals(self):
        """Ensure displayed totals use PF-inclusive Untaxed amount."""
        res = super()._compute_tax_totals()
        group_name = _('Untaxed Amount')
        for order in self:
            currency = order.currency_id
            tax_totals = order.tax_totals
            order_lines = order.order_line.filtered(lambda l: not l.display_type)
            first_line = order_lines[:1]
            if first_line and first_line.tax_id:
                real_tax_name = first_line.tax_id[0].tax_group_id.name
            else:
                real_tax_name = _('Taxes')
            tax_totals['groups_by_subtotal'] = {
                group_name: [{
                    'tax_group_name':real_tax_name,
                    'tax_group_amount': order.amount_tax,
                    'tax_group_base_amount': order.amount_untaxed_with_pf,
                    'formatted_tax_group_amount': formatLang(self.env, order.amount_tax, currency_obj=currency),
                    'formatted_tax_group_base_amount': formatLang(self.env, order.amount_untaxed_with_pf, currency_obj=currency),
                    'tax_group_id': 1,
                    'group_key': 1,
                    'hide_base_amount': False,
                }]
            }
            tax_totals['subtotals'] = [{
                'name': group_name,
                'amount': order.amount_untaxed_with_pf,
                'formatted_amount': formatLang(self.env, order.amount_untaxed_with_pf, currency_obj=currency),
            }]
            tax_totals['amount_total'] = order.amount_total
            tax_totals['amount_untaxed'] = order.amount_untaxed_with_pf
            tax_totals['formatted_amount_total'] = formatLang(self.env, order.amount_total, currency_obj=currency)
            tax_totals['subtotals_order'] = [group_name]

            order.tax_totals = tax_totals

        return res


    def action_open_pf_charges_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add P&F Charges',
            'res_model': 'pf.charges.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id, 'default_percentage': self.pf_percentage},
        }
    gr_no = fields.Char(string="GR/RR No.")
    transport = fields.Char(string="Transport")
    vehicle_no = fields.Char(string="Vehicle No.")
    po_number = fields.Char(string="PO Number")
    po_date = fields.Date(string="PO Date")
    transport_type = fields.Char(string="Transport Type")
    way_bill_no = fields.Char(string="E-Way Bill No.")

    is_enabled_roundoff = fields.Boolean(string="Apply Roundoff", default=True)
    amount_roundoff = fields.Monetary(string='Amount (Rounded)', compute='_compute_amount_roundoff', store=True)
    amount_total_rounded = fields.Monetary(string='Total (Rounded)', compute='_compute_amount_roundoff', store=True)

    # @api.depends('amount_total', 'amount_total_with_pf','currency_id', 'is_enabled_roundoff')
    # def _compute_amount_roundoff(self):
    #     for order in self:
    #         if order.is_enabled_roundoff:
    #             # Use total including P&F if available
    #             base_total = order.amount_total_with_pf if order.amount_total_with_pf else order.amount_total
    #             rounded_total = round(base_total)
    #             order.amount_roundoff = rounded_total - base_total
    #             order.amount_total_rounded = rounded_total
    #         else:
    #             order.amount_roundoff = 0.0
    #             order.amount_total_rounded = order.amount_total_with_pf or order.amount_total
    
    def _prepare_picking(self):
        res = super(SaleOrder, self)._prepare_picking()
        res.update({
            'gr_no': self.gr_no,
            'transport': self.transport,
            'vehicle_no': self.vehicle_no,
            'po_number': self.po_number,
            'po_date': self.po_date,
            # 'transport_type': self.transport_type,
            # 'way_bill_no': self.way_bill_no,
        })
        return res
    
    ##################### New code to show lot/serial wise data on sales order:Starts ##################################
    show_lot_wise = fields.Boolean(string="Show Lot-wise Data", default=False, copy=False)
    lot_id = fields.Many2one('stock.lot', string="Lot", readonly=True)
    def action_split_lines_by_lot(self):
        SalesLine = self.env['sale.order.line']

        for order in self:
            # Remove previously generated lot-split lines
            old_lines = order.order_line.filtered(lambda l: l.is_lot_split_line)
            old_lines.unlink()

            for line in order.order_line.filtered(
                lambda l: not l.display_type and not l.is_lot_split_line
            ):
                moves = line.move_ids.filtered(lambda m: m.state == 'done')
                if not moves:
                    continue

                lot_qty_map = {}

                for move in moves:
                    for ml in move.move_line_ids:
                        if ml.lot_id:
                            lot_qty_map.setdefault(ml.lot_id.name, 0.0)
                            lot_qty_map[ml.lot_id.name] += ml.quantity

                if not lot_qty_map:
                    continue

                seq = line.sequence + 0.01

                # Create lot-wise NOTE lines under the current line
                for lot_name, qty in lot_qty_map.items():
                    SalesLine.create({
                        'order_id': order.id,
                        'display_type': 'line_note',
                        'name': f"{lot_name} → Qty Delivered: {qty}",
                        'product_uom_qty': 0.0,
                        'sequence': seq,
                        'is_lot_split_line': True,
                    })
                    seq += 0.01

    def action_toggle_lot_wise(self):
        for order in self:
            if order.show_lot_wise:
                # HIDE → remove lot split lines
                order.order_line.filtered(lambda l: l.is_lot_split_line).unlink()
                order.show_lot_wise = False
            else:
                # SHOW → reuse existing logic
                order.action_split_lines_by_lot()
                order.show_lot_wise = True

    # Code to populate the validated serial numbers on the invoice
    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        for invoice in invoices:
            # Exclude lot split lines from being added to invoice lines
            invoice_line_ids_to_remove = invoice.invoice_line_ids.filtered(
                lambda l: l.sale_line_ids.filtered(lambda sl: sl.is_lot_split_line)
            )
            if invoice_line_ids_to_remove:
                invoice_line_ids_to_remove.unlink()

            for inv_line in invoice.invoice_line_ids:
                sale_lines = inv_line.sale_line_ids.filtered(lambda l: not l.is_lot_split_line)
                if not sale_lines:
                    continue

                qty_to_assign = inv_line.quantity

                # Use quantity_done for delivered qty in Odoo 17
                move_lines = (
                    sale_lines
                    .mapped('move_ids')
                    .filtered(lambda m: m.state == 'done')
                    .mapped('move_line_ids')
                    .filtered(
                        lambda ml: ml.lot_id and ml.invoiced_qty_custom < ml.quantity
                    )
                    .sorted(key=lambda ml: ml.date)
                )

                for ml in move_lines:
                    if qty_to_assign <= 0:
                        break

                    remaining_qty = ml.quantity - ml.invoiced_qty_custom
                    consume_qty = min(remaining_qty, qty_to_assign)

                    ml.invoiced_qty_custom += consume_qty
                    ml.invoice_line_id_custom = inv_line.id

                    qty_to_assign -= consume_qty

        return invoices

##################### New code to show lot/serial wise data on sales order:Ends ##################################

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    lot_numbers = fields.Char(string="Lot Numbers", compute="_compute_lot_numbers", store=False)

    def _compute_lot_numbers(self):
        for line in self:
            lot_names = set()

            # Stock moves created from this PO line
            moves = line.move_ids.filtered(lambda m: m.state == 'done')

            # Move lines contain lot info
            for move in moves:
                for move_line in move.move_line_ids:
                    if move_line.lot_id:
                        lot_names.add(move_line.lot_id.name)

            line.lot_numbers = ', '.join(sorted(lot_names)) if lot_names else ''
            
    ############ code to add purchase status field in purchase history tree view #########
    
    # (NEW) Field to mark lot split lines to show under purchase order lines
    is_lot_split_line = fields.Boolean(string="Lot Split Line", default=False, copy=False, index=True)


class PFChargesWizard(models.TransientModel):
    _name = "pf.charges.wizard"
    _description = "P&F Charges Wizard"

    percentage = fields.Float(string="P&F Percentage (%)", required=True)
    order_id = fields.Many2one('sale.order', string="Sale Order")

    def action_apply_pf_charges(self):
        self.ensure_one()
        order = self.order_id

        if order:
            order.pf_percentage = self.percentage
            order._compute_amounts()  # force recompute

        # Force reload the form view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
            'target': 'current',
        }

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def amount_to_text_indian(self, amount):
        """
        Convert amount to Indian currency words with paise.
        Example: 141955.42 -> 'One Lakh Forty One Thousand Nine Hundred Fifty Five And Forty Two Paise'
        """
        # Split rupees and paise
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))

        # Convert to words (Indian numbering system) and remove 'And' inside rupees
        rupees_words = num2words(rupees, lang='en_IN').replace(',', '').replace(' And', '').title()

        if paise > 0:
            paise_words = num2words(paise, lang='en_IN').replace(',', '').title()
            return f"{rupees_words} And {paise_words} Paise"
        else:
            return f"{rupees_words}"


##################### Code relating to show serail/lot numbers on the Invoices: Starts #####################
class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    invoice_line_id_custom = fields.Many2one(
        'account.move.line',
        string='Invoice Line (Custom)',
        index=True
    )

    invoiced_qty_custom = fields.Float(
        string='Invoiced Quantity',
        default=0.0
    )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_numbers = fields.Char(
        string="Delivered Serial / Lot Numbers",
        compute="_compute_lot_numbers",
        store=False
    )

    def _compute_lot_numbers(self):
        for line in self:
            move_lines = self.env['stock.move.line'].search([
                ('invoice_line_id_custom', '=', line.id),
                ('lot_id', '!=', False),
            ])

            line.lot_numbers = ', '.join(
                sorted(set(move_lines.mapped('lot_id.name')))
            )

##################### Code relating to show serail/lot numbers on the Invoices: Starts #####################


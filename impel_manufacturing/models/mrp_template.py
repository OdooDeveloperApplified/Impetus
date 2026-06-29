from odoo import models,fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    internal_transfer_count = fields.Integer(
        string="Internal Transfers",
        compute="_compute_internal_transfer_count"
    )

    def _compute_internal_transfer_count(self):
        for mo in self:
            count = self.env['stock.picking'].search_count([
                ('origin', '=', mo.name),
                ('picking_type_id.code', '=', 'internal')
            ])
            mo.internal_transfer_count = count
    
    def action_view_internal_transfers(self):
        self.ensure_one()

        pickings = self.env['stock.picking'].search([
            ('origin', '=', self.name),
            ('picking_type_id.code', '=', 'internal')
        ])

        action = {
            'name': 'Internal Transfers',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pickings.ids)],
            'context': {'default_origin': self.name},
        }

        if len(pickings) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': pickings.id,
            })

        return action

    def action_create_internal_transfer(self):

        for mo in self:

            if not mo.move_raw_ids:
                raise UserError("No components to transfer.")

            # Locations
            stock_location = mo.picking_type_id.default_location_src_id

            assembly_location = self.env['stock.location'].sudo().search([
                ('complete_name', 'ilike', 'Assembly')
            ], limit=1)

            if not assembly_location:
                raise UserError("Assembly location not found.")

            # Picking Type
            picking_type = self.env['stock.picking.type'].sudo().search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', mo.picking_type_id.warehouse_id.id)
            ], limit=1)

            if not picking_type:
                raise UserError("Internal picking type not found.")

            # Avoid duplicate
            existing = self.env['stock.picking'].sudo().search([
                ('origin', '=', mo.name),
                ('picking_type_id', '=', picking_type.id)
            ], limit=1)

            if existing:
                raise UserError("Internal transfer already exists for this MO.")

            # Create Picking
            picking = self.env['stock.picking'].sudo().create({
                'picking_type_id': picking_type.id,
                'location_id': stock_location.id,
                'location_dest_id': assembly_location.id,
                'origin': mo.name,
            })

            for move in mo.move_raw_ids:
                if move.product_id.type != 'product':
                    continue

                self.env['stock.move'].sudo().create({
                    'name': move.product_id.display_name,
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'picking_id': picking.id,
                    'location_id': stock_location.id,
                    'location_dest_id': assembly_location.id,
                    'origin': mo.name,
                })

            picking.action_confirm()
            picking.action_assign()

            # Update MO source location
            mo.location_src_id = assembly_location.id

        return True
    
    length = fields.Float(string='Length (mm)')

    @api.onchange('length')
    def _onchange_length(self):
        self._compute_dynamic_components()

    def write(self, vals):
        res = super().write(vals)
        if 'length' in vals:
            self._compute_dynamic_components()

        return res

    def action_confirm(self):
        res = super().action_confirm()
        self._compute_dynamic_components()
        return res

    def _compute_dynamic_components(self):
        """
        Update raw material quantities based on formulas.
        """
        for production in self:
            if not production.bom_id:
                continue
            for move in production.move_raw_ids:
                bom_line = production.bom_id.bom_line_ids.filtered(lambda l: l.product_id == move.product_id)

                if not bom_line:
                    continue

                bom_line = bom_line[0]

                if not bom_line.formula_qty:
                    continue

                localdict = {
                    'length': production.length or 0,
                }

                try:
                    qty = safe_eval(
                        bom_line.formula_qty,
                        localdict,
                        mode="eval"
                    )

                    move.product_uom_qty = qty

                except Exception:
                    continue

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    formula_qty = fields.Char(string='Quantity Formula', help="""
        Examples:
        length
        length - 100
        (length / 2) + 50
        """)
# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    move_orig_fifo_ids = fields.Many2many(
        'stock.move', 'stock_move_move_fifo_rel', 'move_dest_id',
        'move_orig_id', 'Original Fifo Move',
        help="Optional: previous stock move when chaining them")

    def _action_done(self, cancel_backorder=False):
        for move in self:
            if not move._is_out():
                continue
            product = move.product_id
            if product.cost_method not in ('average', 'fifo'):
                continue

            # TODO: Could have more than one move. Should loop on the quantities
            move_orig = product._run_fifo_get_stack(move._get_valued_qty())[:0]
            if move_orig:
                move.write({'move_orig_fifo_ids': [(4, move_orig.id, 0)]})
        return super()._action_done(cancel_backorder=cancel_backorder)

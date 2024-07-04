# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from lxml import html


class StockMove(models.Model):
    _inherit = 'stock.move'

    check_id = fields.One2many('quality.check', 'move_id')
    note = fields.Html('Note', related='check_id.note')
    worksheet_document = fields.Binary('Worksheet Image/PDF', compute='_compute_worksheet_document')
    worksheet_note = fields.Html('Worksheet description', related='check_id.workorder_id.operation_id.note')

    @api.depends('check_id.worksheet_document', 'check_id.source_document', 'check_id.workorder_id.operation_id.worksheet')
    def _compute_worksheet_document(self):
        for record in self:
            if record.check_id:
                record.worksheet_document = record.check_id.worksheet_document if record.check_id.source_document == "step" else record.check_id.workorder_id.operation_id.worksheet
            else:
                record.worksheet_document = None

    @api.depends('workorder_id')
    def _compute_manual_consumption(self):
        super()._compute_manual_consumption()
        for move in self:
            if move.product_id in move.workorder_id.check_ids.component_id and \
            move.product_id not in move.raw_material_production_id.workorder_ids.check_ids.component_id:
                move.manual_consumption = True

    def _should_bypass_set_qty_producing(self):
        production = self.raw_material_production_id or self.production_id
        if production and ((self.product_id in production.workorder_ids.quality_point_ids.component_id) or self.operation_id):
            return True
        return super()._should_bypass_set_qty_producing()

    def _action_assign(self, force_qty=False):
        res = super()._action_assign(force_qty=force_qty)
        for workorder in self.raw_material_production_id.workorder_ids:
            for check in workorder.check_ids:
                if check.test_type not in ('register_consumed_materials', 'register_byproducts'):
                    continue
                check.write(workorder._defaults_from_move(check.move_id))
        return res

    def action_show_details_quality_check(self):
        self.ensure_one()
        view = self.env.ref('mrp_workorder.view_stock_move_operations_quality_check')
        return {
            'name': (self.check_id.title or _('Detailed Operations')) + f' - {self.product_id.name}, {self.product_uom_qty} {self.product_uom.name}',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context,
                dialog_size='extra-large',
                active_mo_id=self.raw_material_production_id.id
            ),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_quality_check(self):
        self.env['quality.check'].search([('move_id', 'in', self.ids)]).unlink()

    def action_add_from_catalog_raw(self):
        mo = self.env['mrp.production'].browse(self.env.context.get('order_id'))
        return mo.with_context(child_field='move_raw_ids', from_shop_floor=self.env.context.get('from_shop_floor')).action_add_from_catalog()

    def action_pass(self):
        for check in self.check_id:
            check.action_next()
        return True

from ast import literal_eval

from odoo import Command, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    role_sync_shift_rental = fields.Boolean(related='role_id.sync_shift_rental')

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get('rental_order_updated')
            and any(vals.get(k) for k in ['start_datetime', 'end_datetime'])
            and (rental_orders := self.exists().filtered('role_sync_shift_rental').sale_order_id.filtered('is_rental_order'))
        ):
            shifts_per_sale_order = self.env['planning.slot']._read_group(
                [
                    ('sale_order_id', 'in', rental_orders.ids),
                ],
                ['sale_order_id'],
                ['id:recordset'],
            )
            updated_sale_order_ids = []
            for sale_order, shifts in shifts_per_sale_order:
                min_start_datetime = min(shifts.mapped('start_datetime'))
                max_end_datetime = max(shifts.mapped('end_datetime'))
                rental_order_vals = {}
                if sale_order.rental_start_date != min_start_datetime:
                    rental_order_vals['rental_start_date'] = min_start_datetime
                if sale_order.rental_return_date != max_end_datetime:
                    rental_order_vals['rental_return_date'] = max_end_datetime
                if rental_order_vals:
                    sale_order.sudo().with_context(slots_rescheduled=True).write(rental_order_vals)
                    updated_sale_order_ids.append(sale_order.id)
            if updated_sale_order_ids:
                SaleOrderLine = self.env['sale.order.line']
                self.env.add_to_compute(
                    SaleOrderLine._fields['name'],
                    SaleOrderLine.sudo().search([('order_id', 'in', updated_sale_order_ids), ('is_rental', '=', True)])
                )
        return res

    def action_create_order(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale_renting.rental_order_action')
        context = literal_eval(action.get('context', '{}'))
        context.update(
            default_is_rental_order=True,
            default_rental_start_date=self.start_datetime,
            default_rental_return_date=self.end_datetime,
        )
        if products := self.role_id.product_ids.filtered('rent_ok'):
            context['default_order_line'] = [
                Command.create({
                    'product_id': products[0].product_variant_id.id,
                    'is_rental': True,
                    'product_uom_qty': 1,
                    'planning_slot_ids': self.ids,
                }),
            ]
        return {
            **action,
            'view_mode': 'form',
            'views': [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form'],
            'target': 'new',
            'context': context,
        }

    def action_add_last_order(self):
        self.ensure_one()
        order = self.env['sale.order'].search([
            ('is_rental_order', '=', True),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if not order:
            raise ValidationError(self.env._('No Rental Order is found.'))
        products = self.role_id.product_ids.filtered('rent_ok')
        for sol in order.order_line:
            if sol.product_template_id in products and float_compare(sol.planning_hours_to_plan, 0) == 0:
                self.sale_line_id = sol
                break
        if not self.sale_line_id:
            self.sale_line_id = self.env['sale.order.line'].create({
                'product_id': products[:1].product_variant_id.id,
                'is_rental': True,
                'product_uom_qty': 1,
                'order_id': order.id,
            })
        self.state = 'published'
        if not (order.rental_start_date == self.start_datetime and order.rental_return_date == self.end_datetime):
            min_start_datetime, max_end_datetime = self.env['planning.slot']._read_group(
                [('sale_order_id', '=', order.id)],
                [],
                ['start_datetime:min', 'end_datetime:max'],
            )[0]
            order.with_context(slots_rescheduled=True).write({'rental_start_date': min_start_datetime, 'rental_return_date': max_end_datetime})
            SaleOrderLine = self.env['sale.order.line']
            self.env.add_to_compute(
                SaleOrderLine._fields['name'],
                order.order_line.filtered('is_rental')
            )

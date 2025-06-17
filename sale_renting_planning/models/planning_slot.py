from ast import literal_eval

from odoo import Command, fields, models
from odoo.exceptions import ValidationError


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    role_sync_shift_rental = fields.Boolean(related='role_id.sync_shift_rental')

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
            if sol.product_template_id in products:
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

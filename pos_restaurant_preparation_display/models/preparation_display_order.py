from odoo import models, fields, api, _


class Pos_Preparation_DisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    pos_table_id = fields.Many2one('restaurant.table')
    pos_course_id = fields.Many2one('restaurant.order.course')

    @api.model_create_multi
    def create(self, vals_list):
        course_id = self._context.get('po_course_id', None)
        if course_id:
            for vals in vals_list:
                if not vals.get('pos_course_id', None):
                    vals['pos_course_id'] = course_id
        return super().create(vals_list)

    def _export_for_ui(self, preparation_display):
        order_for_ui = super()._export_for_ui(preparation_display)

        if order_for_ui:
            order_for_ui['customer_count'] = self.pos_order_id.customer_count
            order_for_ui['table'] = {
                'id': self.pos_order_id.table_id.id,
                'seats': self.pos_order_id.table_id.seats,
                'table_number': self.pos_order_id.table_id.table_number,
                'color': self.pos_order_id.table_id.color,
            }
            if self.pos_course_id:
                order_for_ui['course'] = {
                    'index': self.pos_course_id.index,
                    'fired': self.pos_course_id.fired,
                    'fired_date': self.pos_course_id.fired_date,
                }
            order_for_ui['floating_order_name'] = self.pos_order_id.floating_order_name

        return order_for_ui

    def _get_preparation_order_values(self, order):
        order_to_create = super()._get_preparation_order_values(order)

        if order.get('pos_table_id'):
            order_to_create['pos_table_id'] = order['pos_table_id']

        return order_to_create

    @api.model
    def process_order(self, order_id, cancelled=False, general_customer_note=None, note_history=None, internal_note=None):
        order = self.env['pos.order'].browse(order_id)
        if not order:
            return

        res = True
        if cancelled or not order.course_ids:
            res = super().process_order(order_id, cancelled, general_customer_note, note_history, internal_note)
        else:
            # Split display order by course
            data_change = None
            course_update_notifications = []
            for course_id in order.course_ids:
                course_already_fired = (course_id.fired and
                                        self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order.id), ('pos_course_id', '=', course_id.id)], limit=1))
                course_lines_uuids = course_id.line_ids.mapped(lambda l: l.uuid)
                order_line_filer = lambda line_uuid: line_uuid in course_lines_uuids
                data = (order.with_context(ppc_order_line_filter=order_line_filer, po_course_id=course_id.id)
                        ._process_preparation_changes(cancelled, general_customer_note, note_history, internal_note))
                if data.get('change'):
                    if not data_change:
                        data_change = data
                    elif data_change and data.get('category_ids'):
                        # Merge change categories
                        category_ids = data_change.get('category_ids', [])
                        category_ids.update(data.get('category_ids'))
                        data_change['category_ids'] = category_ids
                    if data.get('sound'):
                        data_change['sound'] = True
                    if course_already_fired and data.get('order_added'):
                        course_update_notifications.append({
                            'category_ids': data.get('category_ids'),
                            'notification': _("Course %s Updated", str(course_id.index))
                        })
            if data_change:
                self._send_order_to_preparation_displays(order, data_change)
                for notification in course_update_notifications:
                    self._send_notification_to_preparation_displays(order, notification)

        if order and order.table_id:
            old_orders = self.env['pos_preparation_display.order'].search([('id', '=', order_id), ('pos_table_id', '!=', order.table_id.id)])
            for o in old_orders:
                o.pos_table_id = order.table_id

        return res

    @api.model
    def fire_course(self, course_id):
        if not course_id:
            return
        course = self.env['restaurant.order.course'].browse(course_id)
        if not course:
            return
        order = course.order_id
        course_msg = _("Course %s Fired", str(course.index))
        data = {
            'change': True,
            'category_ids': course.line_ids.mapped('product_id.pos_categ_ids.id'),
            'sound': True,
            'notification': f"{self._get_table_name(order.table_id)} {course_msg}"
        }
        self._send_order_to_preparation_displays(order, data)

    def _get_order_name(self):
        order = self.pos_order_id
        if order.session_id.config_id.module_pos_restaurant:
            if not order.table_id and not order.floating_order_name:
                return _("Direct Sale")

            if order.table_id:
                name = self._get_table_name(order.table_id)
                if self.pos_course_id:
                    name += f" - C{self.pos_course_id.index}"
                return name

        return super()._get_order_name()

    @api.model
    def _get_table_name(self, table):
        if not table:
            return ""
        name = f"T{table.table_number}"
        if table.parent_id:
            name += f" &{table.parent_id.table_number}"
        return name

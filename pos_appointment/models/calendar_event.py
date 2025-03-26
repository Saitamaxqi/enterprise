# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from datetime import timedelta


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ["calendar.event", "pos.load.mixin"]

    answers = fields.Char('Q&A answers', compute='_compute_answers')

    @api.depends('appointment_answer_input_ids')
    def _compute_answers(self):
        for record in self:
            record.answers = (', ').join([answer.value_text_box or answer.value_answer_id.name for answer in record.appointment_answer_input_ids.sorted('id')])

    @api.model
    def _load_pos_data_domain(self, data):
        now = fields.Datetime.now()
        dayAfter = fields.Date.today() + timedelta(days=1)
        appointment_type_id = [config['appointment_type_id'] for config in data['pos.config']]
        return [
            ('booking_line_ids.appointment_resource_id', '=', False),
            ('appointment_type_id', 'in', appointment_type_id),
            '|', '&', ('start', '>=', now), ('start', '<=', dayAfter), '&', ('stop', '>=', now), ('stop', '<=', dayAfter),
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'start', 'duration', 'stop', 'name', 'appointment_type_id', 'appointment_status', 'appointment_resource_ids', 'resource_total_capacity_reserved']

    def action_open_booking_gantt_view(self):
        return {
            'name': 'Manage Bookings',
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            "views": [(self.env.ref("pos_appointment.calendar_event_view_gantt_booking_resource_inherited_pos_appointment").id, "gantt"), (False, 'list'), (False, 'calendar'), (False, 'pivot')],
            'target': 'current',
            'context': {
                'appointment_booking_gantt_show_all_resources': True,
                'active_model': 'appointment.type',
                'default_partner_ids': [],
                'default_duration': 2,
                'default_resource_total_capacity_reserved': 2,
                "search_default_appointment_type_id": self._context.get("appointment_type_id"),
                "no_breadcrumbs": True,
                'hide_no_content_helper': True,
            }
        }

    def action_open_booking_form_view(self):
        return {
            'name': 'Edit Booking',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'views': [(self.env.ref('pos_pos_appointment.calendar_event_view_form_gantt_booking_inherited_pos_appointment').id, 'form')],
            'res_id': self.id,
        }

    def set_attended(self):
        self.appointment_status = 'attended'

    def set_cancelled(self):
        self.appointment_status = 'cancelled'

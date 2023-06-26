# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTicketCreateTimesheet(models.TransientModel):
    _name = 'helpdesk.ticket.create.timesheet'
    _description = "Create Timesheet from ticket"

    time_spent = fields.Float('Time Spent')
    description = fields.Char('Description')
    ticket_id = fields.Many2one(
        'helpdesk.ticket', "Ticket", required=True,
        default=lambda self: self.env.context.get('active_id', None),
        help="Ticket for which we are creating a sales order",
    )

    def action_generate_timesheet(self):
        timesheet = self.ticket_id.user_time_id._get_related_document()
        timesheet.write({
            'name': self.description,
            'unit_amount': self.time_spent,
        })
        self.ticket_id.user_timer_id.unlink()
        return timesheet

    def action_delete_timesheet(self):
        timesheet = self.ticket_id.user_timer_id._get_related_document()
        self.ticket_id.user_timer_id.unlink()
        timesheet.unlink()

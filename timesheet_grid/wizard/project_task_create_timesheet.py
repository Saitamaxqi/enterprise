# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTaskCreateTimesheet(models.TransientModel):
    _name = 'project.task.create.timesheet'
    _description = "Create Timesheet from task"

    _time_positive = models.Constraint(
        'CHECK(time_spent > 0)',
        "The timesheet's time must be positive",
    )

    time_spent = fields.Float('Time Spent')
    description = fields.Char('Description', compute='_compute_description', store=True, readonly=False)
    task_id = fields.Many2one(
        'project.task', "Task", required=True,
        default=lambda self: self.env.context.get('active_id', None),
        help="Task for which we are creating a sales order",
    )

    def _compute_description(self):
        for wizard in self:
            if not wizard.description:
                timesheet = wizard.task_id.user_timer_id._get_related_document()
                if timesheet and timesheet.name and timesheet.name != '/':
                    wizard.description = timesheet.name

    def save_timesheet(self):
        timesheet = self.task_id.user_timer_id._get_related_document()
        self.task_id.user_timer_id.unlink()
        timesheet.write({
            'name': self.description,
            'unit_amount': self.time_spent,
        })
        return timesheet

    def action_delete_timesheet(self):
        timesheet = self.task_id.user_timer_id._get_related_document()
        self.task_id.user_timer_id.unlink()
        timesheet.unlink()

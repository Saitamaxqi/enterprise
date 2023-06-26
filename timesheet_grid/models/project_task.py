# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ["project.task", "timer.mixin", "timesheet.grid.mixin"]

    display_timesheet_timer = fields.Boolean("Display Timesheet Time", compute='_compute_display_timesheet_timer', export_string_translation=False)

    @api.depends('allow_timesheets', 'analytic_account_active')
    def _compute_display_timesheet_timer(self):
        for task in self:
            task.display_timesheet_timer = task.allow_timesheets and task.analytic_account_active and not task.encode_uom_in_days

    def _compute_allocated_hours(self):
        # Only change values when creating a new record from the gantt view
        # or the existing tasks that doesn't allow timesheets
        timsheeted_tasks = self.filtered(lambda task: task._origin and task.allow_timesheets)
        super(ProjectTask, self - timsheeted_tasks)._compute_allocated_hours()

    @api.onchange('project_id')
    def _onchange_project_id(self):
        # If task has non-validated timesheets AND new project has not the timesheets feature enabled, raise a warning notification
        if not all(t.validated for t in self.timesheet_ids) and not self.project_id.allow_timesheets:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _("Moving this task to a project without timesheet support will retain timesheet drafts in the original project. "
                                 "Although they won't be visible here, you can still edit them using the Timesheets app."),
                    'type': "notification",
                },
            }

    def _set_allocated_hours_for_tasks(self):
        super(ProjectTask, self.filtered(lambda task: not task.allow_timesheets))._set_allocated_hours_for_tasks()

    def _gantt_progress_bar_project_id(self, res_ids):
        timesheet_read_group = self.env['account.analytic.line'].sudo()._read_group(
            [('project_id', 'in', res_ids)],
            ['project_id'],
            ['unit_amount:sum'],
        )
        return {
            project.id: {
                'value': unit_amount_sum,
                'max_value': project.sudo().allocated_hours,
            }
            for project, unit_amount_sum in timesheet_read_group
        }

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'project_id':
            return dict(
                self._gantt_progress_bar_project_id(res_ids),
                warning=_("This project isn't expected to have task during this period."),
            )
        return super()._gantt_progress_bar(field, res_ids, start, stop)

    def action_view_subtask_timesheet(self):
        action = super().action_view_subtask_timesheet()
        grid_view_id = self.env.ref('timesheet_grid.timesheet_view_grid_by_employee').id
        action['views'] = [
            [grid_view_id, view_mode] if view_mode == 'grid' else [view_id, view_mode]
            for view_id, view_mode in action['views']
        ]
        return action

    def action_timer_start(self):
        if not self.user_timer_id.timer_start and self.display_timesheet_timer:
            super().action_timer_start()

    def action_timer_stop(self):
        # timer was either running or paused
        if self.user_timer_id.timer_start and self.display_timesheet_timer:
            rounded_hours = self.env['account.analytic.line'].get_rounded_time(self.user_timer_id._get_minutes_spent())
            return self._action_open_new_timesheet(rounded_hours)
        return False

    def _action_open_new_timesheet(self, time_spent):
        return {
            "name": _("Confirm Time Spent"),
            "type": 'ir.actions.act_window',
            "res_model": 'project.task.create.timesheet',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                **self.env.context,
                'active_id': self.id,
                'active_model': self._name,
                'default_time_spent': time_spent,
                'dialog_size': 'medium',
            },
        }

    def get_allocated_hours_field(self):
        return 'allocated_hours'

    def get_worked_hours_fields(self):
        return ['effective_hours', 'subtask_effective_hours']

    def _get_hours_to_plan(self):
        return self.remaining_hours

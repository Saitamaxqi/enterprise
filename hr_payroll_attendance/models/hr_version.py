from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _preprocess_work_hours_data(self, work_data, date_from, date_to):
        """
        Removes extra hours from attendance work data and add a new entry for extra hours
        """
        attendance_contracts = self.filtered(lambda c: c.work_entry_source == 'attendance' and c.wage_type == 'hourly')
        work_entry_type_overtime = self.env.ref('hr_work_entry.work_entry_type_overtime', False)
        default_work_entry_type = self.structure_type_id.default_work_entry_type_id
        if not attendance_contracts or not work_entry_type_overtime or len(default_work_entry_type) != 1:
            return
        overtime_hours = self.env['hr.attendance.overtime']._read_group(
            [('employee_id', 'in', self.employee_id.ids),
                ('date', '>=', date_from), ('date', '<=', date_to)],
            [], ['duration:sum'],
        )[0][0]
        # unapproved overtimes should not be taken into account
        unapproved_overtime_hours = round(self.env['hr.attendance'].sudo()._read_group([
            ('employee_id', 'in', self.employee_id.ids),
            ('check_in', '>=', date_from),
            ('check_out', '<=', date_to),
            ('overtime_hours', '>', 0),
            ('overtime_status', '!=', 'approved')],
            [], ['overtime_hours:sum'],
        )[0][0], 2)
        if not overtime_hours or overtime_hours < 0:
            return
        work_data[default_work_entry_type.id] -= overtime_hours
        overtime_hours -= unapproved_overtime_hours
        if overtime_hours > 0:
            work_data[work_entry_type_overtime.id] = overtime_hours

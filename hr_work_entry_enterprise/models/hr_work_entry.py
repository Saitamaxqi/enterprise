# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

import pytz
from odoo import api, models
from odoo.fields import Domain
from odoo.tools.intervals import Intervals
from odoo.tools.date_utils import localized


class HrWorkEntry(models.Model):
    _inherit = "hr.work.entry"

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=None, progress_bar_fields=None, start_date=None, stop_date=None, scale=None):
        """
        We override get_gantt_data to allow the display of open-ended records,
        We also want to add in the gantt rows, the active emloyees that have a check in in the previous 60 days
        """
        additional_domain = Domain(domain) & Domain(self.env.context.get('active_domain') or Domain.TRUE)
        domain = additional_domain & Domain("date", "<=", stop_date) & Domain("date", ">", start_date)
        gantt_data = super().get_gantt_data(domain, groupby, read_specification, limit=limit, offset=offset, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)

        if groupby and groupby[0] == 'employee_id':
            employees_in_contract_ids = self.env["hr.employee"]._get_contract_versions(date_start=start_date, date_end=stop_date).keys()
            employees_with_work_entries_ids = [group['employee_id'][0] for group in gantt_data['groups']]
            employees_without_work_entries_ids = employees_in_contract_ids - employees_with_work_entries_ids

            employees_without_work_entries_domain = additional_domain & Domain('employee_id', 'in', employees_without_work_entries_ids)
            gantt_data_employee_without_work_entries = super().get_gantt_data(employees_without_work_entries_domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)
            for group in gantt_data_employee_without_work_entries['groups']:
                del group['__record_ids']  # Records are not needed here
                gantt_data['groups'].append(group)
                gantt_data['length'] += 1
            if unavailability_fields:
                for field in gantt_data['unavailabilities']:
                    gantt_data['unavailabilities'][field] |= gantt_data_employee_without_work_entries['unavailabilities'][field]
        return gantt_data

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):

        employees_by_calendar = defaultdict(lambda: self.env['hr.employee'])
        employees = self.env['hr.employee'].browse(res_ids)

        # Retrieve for each employee, their period linked to their calendars
        calendar_periods_by_employee = employees._get_calendar_periods(
            localized(start),
            localized(stop),
        )

        full_interval_UTC = Intervals([(
            start.astimezone(pytz.utc),
            stop.astimezone(pytz.utc),
            self.env['resource.calendar'],
        )])

        # calculate the intervals not covered by employee-specific calendars.
        # store these uncovered intervals for each employee.
        # store by calendar, employees involved with them
        periods_without_calendar_by_employee = defaultdict(list)
        for employee, calendar_periods in calendar_periods_by_employee.items():
            employee_interval_UTC = Intervals([])
            for (start, stop, calendar) in calendar_periods:
                calendar_periods_interval_UTC = Intervals([(
                    start.astimezone(pytz.utc),
                    stop.astimezone(pytz.utc),
                    self.env['resource.calendar'],
                )])
                employee_interval_UTC |= calendar_periods_interval_UTC
                employees_by_calendar[calendar] |= employee
            interval_without_calendar = full_interval_UTC - employee_interval_UTC
            if interval_without_calendar:
                periods_without_calendar_by_employee[employee.id] = interval_without_calendar

        # retrieve, for each calendar, unavailability periods for employees linked to this calendar
        unavailable_intervals_by_calendar = {}
        for calendar, employees in employees_by_calendar.items():
            # In case the calendar is not set (fully flexible calendar), we consider the employee as always available
            if not calendar or calendar.flexible_hours:
                unavailable_intervals_by_calendar[calendar] = {
                    employee.id: Intervals([])
                    for employee in employees
                }
                continue

            calendar_work_intervals = calendar._work_intervals_batch(
                localized(start),
                localized(stop),
                resources=employees.resource_id,
                tz=pytz.timezone(calendar.tz)
            )
            full_interval = Intervals([(
                start.astimezone(pytz.timezone(calendar.tz)),
                stop.astimezone(pytz.timezone(calendar.tz)),
                calendar
            )])
            unavailable_intervals_by_calendar[calendar] = {
                employee.id: full_interval - calendar_work_intervals[employee.resource_id.id]
                for employee in employees}

        # calculate employee's unavailability periods based on his calendar's periods
        # (e.g. calendar A on monday and tuesday and calendar b for the rest of the week)
        unavailable_intervals_by_employees = {}
        for employee, calendar_periods in calendar_periods_by_employee.items():
            employee_unavailable_full_interval = Intervals([])
            for (start, stop, calendar) in calendar_periods:
                interval = Intervals([(start, stop, self.env['resource.calendar'])])
                calendar_unavailable_interval_list = unavailable_intervals_by_calendar[calendar][employee.id]
                employee_unavailable_full_interval |= interval & calendar_unavailable_interval_list
            unavailable_intervals_by_employees[employee.id] = employee_unavailable_full_interval

        flexible_employees = self.env['hr.employee']
        for calendar, employees in employees_by_calendar.items():
            if calendar.flexible_hours:
                flexible_employees |= employees

        result = {}
        for employee_id in res_ids:
            # When an employee doesn't have any calendar,
            # he is considered unavailable for the entire interval
            if employee_id not in unavailable_intervals_by_employees:
                result[employee_id] = [{
                    'start': start.astimezone(pytz.utc),
                    'stop': stop.astimezone(pytz.utc),
                }]
                continue

            # When an employee has a flexible calendar,
            # he is considered available for the entire interval
            if employee_id in flexible_employees.ids:
                result[employee_id] = []
                continue

            # When an employee doesn't have a calendar for a part of the entire interval,
            # he will be unavailable for this part
            if employee_id in periods_without_calendar_by_employee:
                unavailable_intervals_by_employees[employee_id] |= periods_without_calendar_by_employee[employee_id]
            result[employee_id] = [{
                'start': interval[0].astimezone(pytz.utc),
                'stop': interval[1].astimezone(pytz.utc),
            } for interval in unavailable_intervals_by_employees[employee_id]]

        return result

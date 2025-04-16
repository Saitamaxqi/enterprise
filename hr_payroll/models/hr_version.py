from datetime import date, datetime
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.osv import expression

import pytz


class HrVersion(models.Model):
    _inherit = 'hr.version'
    _description = 'Employee Contract'

    schedule_pay = fields.Selection([
        ('annually', 'Annually'),
        ('semi-annually', 'Semi-annually'),
        ('quarterly', 'Quarterly'),
        ('bi-monthly', 'Bi-monthly'),
        ('monthly', 'Monthly'),
        ('semi-monthly', 'Semi-monthly'),
        ('bi-weekly', 'Bi-weekly'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily')],
        compute='_compute_schedule_pay', store=True, readonly=False, groups="hr.group_hr_user")
    resource_calendar_id = fields.Many2one(default=lambda self: self.env.company.resource_calendar_id,
        help='''Employee's working schedule.
        When left empty, the employee is considered to have a fully flexible schedule, allowing them to work without any time limit, anytime of the week.
        '''
    )
    hours_per_week = fields.Float(related='resource_calendar_id.hours_per_week', groups="hr.group_hr_user")
    full_time_required_hours = fields.Float(related='resource_calendar_id.full_time_required_hours', groups="hr.group_hr_user")
    is_fulltime = fields.Boolean(related='resource_calendar_id.is_fulltime', groups="hr.group_hr_user")
    wage_type = fields.Selection([
        ('monthly', 'Fixed Wage'),
        ('hourly', 'Hourly Wage')
    ], compute='_compute_wage_type', store=True, readonly=False, groups="hr.group_hr_user")
    hourly_wage = fields.Monetary('Hourly Wage', tracking=True, help="Employee's hourly gross wage.", groups="hr.group_hr_user")
    payslips_count = fields.Integer("# Payslips", compute='_compute_payslips_count', groups="hr_payroll.group_hr_payroll_user")
    calendar_changed = fields.Boolean(help="Whether the previous or next contract has a different schedule or not", groups="hr.group_hr_user")

    time_credit = fields.Boolean('Part Time', readonly=False, groups="hr.group_hr_user")
    work_time_rate = fields.Float(
        compute='_compute_work_time_rate', store=True, readonly=True,
        string='Work time rate', help='Work time rate versus full time working schedule.', groups="hr.group_hr_user")
    standard_calendar_id = fields.Many2one(
        'resource.calendar', default=lambda self: self.env.company.resource_calendar_id, readonly=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", groups="hr.group_hr_user")
    time_credit_type_id = fields.Many2one(
        'hr.work.entry.type', string='Part Time Work Entry Type',
        domain=[('is_leave', '=', True)],
        help="The work entry type used when generating work entries to fit full time working schedule.", groups="hr.group_hr_user")
    is_non_resident = fields.Boolean(string='Non-resident', help='If recipient lives in a foreign country', groups="hr.group_hr_user")
    disabled = fields.Boolean(string="Disabled", help="If the employee is declared disabled by law", groups="hr.group_hr_user", tracking=True)

    @api.depends('structure_type_id')
    def _compute_schedule_pay(self):
        for version in self:
            version.schedule_pay = version.structure_type_id.default_schedule_pay

    @api.depends('structure_type_id')
    def _compute_wage_type(self):
        for version in self:
            version.wage_type = version.structure_type_id.wage_type

    @api.depends('time_credit', 'resource_calendar_id.hours_per_week', 'standard_calendar_id.hours_per_week')
    def _compute_work_time_rate(self):
        for version in self:
            if version.time_credit and version.structure_type_id.default_resource_calendar_id:
                hours_per_week = version.resource_calendar_id.hours_per_week
                hours_per_week_ref = version.structure_type_id.default_resource_calendar_id.hours_per_week
            else:
                hours_per_week = version.resource_calendar_id.hours_per_week
                hours_per_week_ref = version.company_id.resource_calendar_id.hours_per_week
            if not hours_per_week and not hours_per_week_ref:
                version.work_time_rate = 1
            else:
                version.work_time_rate = hours_per_week / (hours_per_week_ref or hours_per_week)

    def _compute_payslips_count(self):
        count_data = self.env['hr.payslip']._read_group(
            [('version_id', 'in', self.ids)],
            ['version_id'],
            ['__count'])
        mapped_counts = {version.id: count for version, count in count_data}
        for version in self:
            version.payslips_count = mapped_counts.get(version.id, 0)

    def _get_salary_costs_factor(self):
        self.ensure_one()
        factors = {
            "annually": 1,
            "semi-annually": 2,
            "quarterly": 4,
            "bi-monthly": 6,
            "monthly": 12,
            "semi-monthly": 24,
            "bi-weekly": 26,
            "weekly": 52,
            "daily": 52 * (self.resource_calendar_id._get_days_per_week() if self.resource_calendar_id else 5),
        }
        return factors.get(self.schedule_pay, super()._get_salary_costs_factor())

    def _is_same_occupation(self, version):
        self.ensure_one()
        contract_type = self.contract_type_id
        work_time_rate = self.resource_calendar_id.work_time_rate
        same_type = contract_type == version.contract_type_id and work_time_rate == version.resource_calendar_id.work_time_rate
        return same_type

    def _get_occupation_dates(self, include_future_contracts=False):
        # Takes several versions and returns all the versions under the same occupation (i.e. the same
        # work rate + the date_from and date_to)
        # include_future_contracts will use versions where the version_date_start is posterior
        # compared to today's date
        result = []
        done_versions = self.env['hr.version']
        date_today = fields.Date.today()

        def remove_gap(version, other_versions, before=False):
            # We do not consider a gap of more than 4 days to be a same occupation
            # other_versions is considered to be ordered correctly in function of `before`
            current_date = version.date_start if before else version.date_end
            for i, other_version in enumerate(other_versions):
                if not current_date:
                    return other_versions[0:i]
                if before:
                    gap = (current_date - other_version.date_end).days
                    current_date = other_version.date_start
                else:
                    gap = (other_version.date_start - current_date).days
                    current_date = other_version.date_end
                if gap >= 4:
                    return other_versions[0:i]
            return other_versions

        for version in self:
            if version in done_versions:
                continue
            versions = version  # hr.version(38,)
            date_from = version.date_start
            date_to = version.date_end
            all_versions = version.employee_id.version_ids.filtered(
                lambda c:
                c != version and
                (c.date_start <= date_today or include_future_contracts)
            )  # hr.version(29, 37, 38, 39, 41) -> hr.version(29, 37, 39, 41)
            before_versions = all_versions.filtered(lambda c: c.date_start < version.date_start)  # hr.version(39, 41)
            before_versions = remove_gap(version, before_versions, before=True)
            after_versions = all_versions.filtered(lambda c: c.date_start > version.date_start).sorted(key='date_start')  # hr.version(37, 29)
            after_versions = remove_gap(version, after_versions)

            for before_version in before_versions:
                if version._is_same_occupation(before_version):
                    date_from = before_version.date_start
                    versions |= before_version
                else:
                    break

            for after_version in after_versions:
                if version._is_same_occupation(after_version):
                    date_to = after_version.date_end
                    versions |= after_version
                else:
                    break
            result.append((versions, date_from, date_to))
            done_versions |= versions
        return result

    def _compute_calendar_changed(self):
        contract_resets = self.filtered(lambda c: not c.resource_calendar_id or not c.active)
        contract_resets.filtered(lambda c: c.calendar_changed).write({'calendar_changed': False})
        self -= contract_resets
        occupation_dates = self._get_occupation_dates(include_future_contracts=True)
        occupation_by_employee = defaultdict(list)
        for row in occupation_dates:
            occupation_by_employee[row[0][0].employee_id.id].append(row)
        contract_changed = self.env['hr.version']
        for occupations in occupation_by_employee.values():
            if len(occupations) == 1:
                continue
            for i in range(len(occupations) - 1):
                current_row = occupations[i]
                next_row = occupations[i + 1]
                contract_changed |= current_row[0][-1]
                contract_changed |= next_row[0][0]
        contract_changed.filtered(lambda c: not c.calendar_changed).write({'calendar_changed': True})
        (self - contract_changed).filtered(lambda c: c.calendar_changed).write({'calendar_changed': False})

    def _get_normalized_wage(self):
        wage = self._get_contract_wage()
        if self.wage_type == 'hourly' or not self.resource_calendar_id.hours_per_week:
            return wage
        else:
            return wage * self._get_salary_costs_factor() / 52 / self.resource_calendar_id.hours_per_week

    def _get_version_work_entries_values(self, date_start, date_stop):
        version_vals = super()._get_version_work_entries_values(date_start, date_stop)
        version_vals += self._get_version_credit_time_values(date_start, date_stop)
        return version_vals

    def _get_version_credit_time_values(self, date_start, date_stop):
        version_vals = []
        for version in self:
            if not version.time_credit or not version.time_credit_type_id:
                continue

            employee = version.employee_id
            resource = employee.resource_id
            calendar = version.resource_calendar_id
            standard_calendar = version.standard_calendar_id

            standard_attendances = standard_calendar._work_intervals_batch(
                pytz.utc.localize(date_start) if not date_start.tzinfo else date_start,
                pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop,
                resources=resource,
                compute_leaves=False)[resource.id]

            attendances = calendar._work_intervals_batch(
                pytz.utc.localize(date_start) if not date_start.tzinfo else date_start,
                pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop,
                resources=resource,
                compute_leaves=False)[resource.id]

            credit_time_intervals = standard_attendances - attendances

            for interval in credit_time_intervals:
                work_entry_type_id = version.time_credit_type_id
                new_vals = {
                    'name': "%s: %s" % (work_entry_type_id.name, employee.name),
                    'date_start': interval[0].astimezone(pytz.utc).replace(tzinfo=None),
                    'date_stop': interval[1].astimezone(pytz.utc).replace(tzinfo=None),
                    'work_entry_type_id': work_entry_type_id.id,
                    'employee_id': employee.id,
                    'version_id': version.id,
                    'company_id': version.company_id.id,
                    'state': 'draft',
                    'is_credit_time': True,
                }
                version_vals.append(new_vals)
        return version_vals

    def _get_work_time_rate(self):
        self.ensure_one()
        return self.work_time_rate if self.time_credit else 1.0

    def _get_contract_wage_field(self):
        self.ensure_one()
        if self.wage_type == 'hourly':
            return 'hourly_wage'
        return super()._get_contract_wage_field()

    @api.model
    def _recompute_calendar_changed(self, employee_ids):
        version_ids = self.search([('employee_id', 'in', employee_ids.ids)], order='contract_date_start asc')
        if not version_ids:
            return
        version_ids._compute_calendar_changed()

    def action_open_payslips(self):
        # [XBO] TODO: to remove if we don't want to display the button in the list view of version
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_view_hr_payslip_month_form")
        action.update({'domain': [('version_id', '=', self.id)]})
        return action

    def _index_contracts(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_hr_payroll_index")
        action['context'] = repr(self.env.context)
        return action

    def _get_work_hours_domain(self, date_from, date_to, domain=None, inside=True):
        if domain is None:
            domain = []
        domain = expression.AND([domain, [
            ('state', 'in', ['validated', 'draft']),
            ('version_id', 'in', self.ids),
        ]])
        if inside:
            domain = expression.AND([domain, [
                ('date_start', '>=', date_from),
                ('date_stop', '<=', date_to)]])
        else:
            domain = expression.AND([domain, [
                '|', '|',
                '&', '&',
                    ('date_start', '>=', date_from),
                    ('date_start', '<', date_to),
                    ('date_stop', '>', date_to),
                '&', '&',
                    ('date_start', '<', date_from),
                    ('date_stop', '<=', date_to),
                    ('date_stop', '>', date_from),
                '&',
                    ('date_start', '<', date_from),
                    ('date_stop', '>', date_to)]])
        return domain

    def _preprocess_work_hours_data(self, work_data, date_from, date_to):
        """
        Method is meant to be overriden, see hr_payroll_attendance
        """
        return

    def get_work_hours(self, date_from, date_to, domain=None):
        # Get work hours between 2 dates (datetime.date)
        # To correctly englobe the period, the start and end periods are converted
        # using the calendar timezone.
        assert not isinstance(date_from, datetime)
        assert not isinstance(date_to, datetime)

        date_from = datetime.combine(fields.Datetime.to_datetime(date_from), datetime.min.time())
        date_to = datetime.combine(fields.Datetime.to_datetime(date_to), datetime.max.time())
        work_data = defaultdict(int)

        versions_by_company_tz = defaultdict(lambda: self.env['hr.version'])
        for version in self:
            # Need to use the tuple (company_id, tz) as the key to avoid issues with different
            # version timezones for the same company.
            versions_by_company_tz[
                version.company_id,
                (version.resource_calendar_id).tz
            ] += version

        # We don't need the timezone immediately here, but we need the uniqueness
        # of the key so that we can guarantee one timezone per set of versions.
        for (company, _unused), versions in versions_by_company_tz.items():
            work_data_tz = versions.with_company(company).sudo()._get_work_hours(date_from, date_to, domain=domain)
            for work_entry_type_id, hours in work_data_tz.items():
                work_data[work_entry_type_id] += hours
        return work_data

    def _get_work_hours(self, date_from, date_to, domain=None):
        """
        Returns the amount (expressed in hours) of work
        for a version between two dates.
        If called on multiple versions, sum work amounts of each version.

        Precondition: the set of versions that this method is called on
        must have the same timezone.
        :param date_from: The start date
        :param date_to: The end date
        :returns: a dictionary {work_entry_id: hours_1, work_entry_2: hours_2}
        """
        assert isinstance(date_from, datetime)
        assert isinstance(date_to, datetime)

        tzs = set((self.resource_calendar_id or self.employee_id.resource_calendar_id).mapped('tz'))
        assert len(tzs) == 1
        version_tz_name = tzs.pop()
        tz = pytz.timezone(version_tz_name) if version_tz_name else pytz.utc
        utc = pytz.timezone('UTC')
        date_from_tz = tz.localize(date_from).astimezone(utc).replace(tzinfo=None)
        date_to_tz = tz.localize(date_to).astimezone(utc).replace(tzinfo=None)

        # First, found work entry that didn't exceed interval.
        work_entries = self.env['hr.work.entry']._read_group(
            self._get_work_hours_domain(date_from_tz, date_to_tz, domain=domain, inside=True),
            ['work_entry_type_id'],
            ['duration:sum']
        )
        work_data = defaultdict(int)
        work_data.update({work_entry_type.id: duration_sum for work_entry_type, duration_sum in work_entries})
        self._preprocess_work_hours_data(work_data, date_from, date_to)

        # Second, find work entry that exceeds interval and compute right duration.
        work_entries = self.env['hr.work.entry'].search(self._get_work_hours_domain(date_from_tz, date_to_tz, domain=domain, inside=False))

        for work_entry in work_entries:
            local_date_start = utc.localize(work_entry.date_start).astimezone(tz).replace(tzinfo=None)
            local_date_stop = utc.localize(work_entry.date_stop).astimezone(tz).replace(tzinfo=None)
            date_start = max(date_from, local_date_start)
            date_stop = min(date_to, local_date_stop)
            if work_entry.work_entry_type_id.is_leave:
                version = work_entry.version_id
                calendar = version.resource_calendar_id
                employee = version.employee_id
                version_data = employee._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar
                )[employee.id]

                work_data[work_entry.work_entry_type_id.id] += version_data.get('hours', 0)
            else:
                work_data[work_entry.work_entry_type_id.id] += work_entry._get_work_duration(date_start, date_stop)  # Number of hours
        return work_data

    def _get_default_work_entry_type_id(self):
        return self.structure_type_id.default_work_entry_type_id.id or super()._get_default_work_entry_type_id()

    def _get_fields_that_recompute_payslip(self):
        # Returns the fields that should recompute the payslip
        return [self._get_contract_wage]

    def _get_nearly_expired_contracts(self, outdated_days, company_id=False):
        today = fields.Date.today()
        nearly_expired_versions = self.search([
            ('company_id', '=', company_id or self.env.company.id),
            ('contract_date_end', '>=', today),
            ('contract_date_end', '<', outdated_days)])

        # Check if no new contracts starting after the end of the expiring one
        nearly_expired_versions_without_new_versions = self.env['hr.version']
        new_versions_grouped_by_employee = {
            employee.id
            for [employee] in self._read_group([
                ('company_id', '=', company_id or self.env.company.id),
                ('contract_date_start', '>=', outdated_days),
                ('employee_id', 'in', nearly_expired_versions.employee_id.ids)
            ], groupby=['employee_id'])
        }

        for expired_version in nearly_expired_versions:
            if expired_version.employee_id.id not in new_versions_grouped_by_employee:
                nearly_expired_versions_without_new_versions |= expired_version
        return nearly_expired_versions_without_new_versions

    @api.model_create_multi
    def create(self, vals_list):
        versions = super().create(vals_list)
        self._recompute_calendar_changed(versions.mapped('employee_id'))
        return versions

    def unlink(self):
        employee_ids = self.mapped('employee_id')
        res = super().unlink()
        self._recompute_calendar_changed(employee_ids)
        return res

    def write(self, vals):
        res = super().write(vals)
        dependendant_fields = self._get_fields_that_recompute_payslip()
        if any(key in dependendant_fields for key in vals):
            for version in self:
                version._recompute_payslips(version.date_start, version.date_end or date.max)
        if any(key in vals for key in ('state', 'date_start', 'resource_calendar_id', 'employee_id')):
            self._recompute_calendar_changed(self.employee_id)
        return res

    def _recompute_work_entries(self, date_from, date_to):
        self.ensure_one()
        super()._recompute_work_entries(date_from, date_to)
        self._recompute_payslips(date_from, date_to)

    def _recompute_payslips(self, date_from, date_to):
        self.ensure_one()
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('version_id', '=', self.id),
            ('state', 'in', ['draft', 'verify']),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('company_id', '=', self.env.company.id),
        ]).filtered(lambda p: p.is_regular)
        if all_payslips:
            all_payslips.action_refresh_from_work_entries()

    def action_new_salary_attachment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Salary Attachment'),
            'res_model': 'hr.salary.attachment',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_ids': self.employee_id.ids}
        }

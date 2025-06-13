# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools.date_utils import get_month


class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pay Run'
    _order = 'date_end desc'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips')
    state = fields.Selection([
        ('01_draft', 'New'),
        ('02_verify', 'Waiting'),
        ('03_close', 'Done'),
        ('04_paid', 'Paid'),
        ('05_cancel', 'Cancelled'),
    ],
        string='Status', index=True, readonly=True, copy=False,
        default='01_draft', tracking=True,
        compute='_compute_state', store=True)
    date_start = fields.Date(
        string='From', readonly=False, required=True,
        compute="_compute_date_start", store=True, precompute=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(
        string='To', readonly=False, required=True,
        compute="_compute_date_end", store=True, precompute=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', readonly=False)
    use_worked_day_lines = fields.Boolean(related='structure_id.use_worked_day_lines')
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
        compute='_compute_schedule_pay', readonly=False, store=True, precompute=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    country_id = fields.Many2one(
        'res.country', string='Country',
        related='company_id.country_id', readonly=True
    )
    country_code = fields.Char(related='country_id.code', depends=['country_id'], readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    payment_report = fields.Binary(
        string='Payment Report',
        help="Export .csv file related to this pay run",
        readonly=True)
    payment_report_filename = fields.Char(readonly=True)
    payment_report_format = fields.Char(readonly=True)
    payment_report_date = fields.Date(readonly=True)
    gross_sum = fields.Monetary(compute="_compute_gross_net_sum", store=True, readonly=True, copy=False)
    net_sum = fields.Monetary(compute="_compute_gross_net_sum", store=True, readonly=True, copy=False)

    def _get_name_for_period(self, vals=None, cache=None):
        if vals is None:
            vals = {}
        if cache is None:
            cache = {}
        if not vals.get("date_start") or not vals.get("date_start"):
            raise UserError(self.env._("You must set a start and end date for the Pay Run"))
        date_start = datetime.fromisoformat(vals.get("date_start"))
        date_end = datetime.fromisoformat(vals.get("date_end"))
        structure_id = vals.get("structure_id")
        name = ""
        format_date_cached = self.env["hr.payslip"]._format_date_cached
        if date_end.year == date_start.year:
            if date_end.month - date_start.month == 11:
                name += format_date_cached(cache, date_start, date_format="Y")
            elif date_end.month == date_start.month:
                if (date_start, date_end) == get_month(date_start):
                    name += format_date_cached(cache, date_start, date_format="MMM Y")
                elif date_start.day == date_end.day:
                    name += format_date_cached(cache, date_start, date_format="d MMM Y")
                else:
                    name += format_date_cached(cache, date_start, date_format="d MMM Y") + " - " + format_date_cached(cache, date_end, date_format="d MMM Y")
            else:
                name += format_date_cached(cache, date_start, date_format="MMM Y") + " - " + format_date_cached(cache, date_end, date_format="MMM Y")
        else:
            name += format_date_cached(cache, date_start, date_format="Y") + " - " + format_date_cached(cache, date_end, date_format="Y")
        if structure_id:
            structure_id = self.env["hr.payroll.structure"].browse(structure_id)
            name += " - " + structure_id.name
        return name

    def _get_employees_domain(self, date_start=None, date_end=None, structure_id=None, company_id=None):
        date_start = date_start or self.date_start
        date_end = date_end or self.date_end
        structure = self.env["hr.payroll.structure"].browse(structure_id) if structure_id else self.structure_id
        company = company_id or self.company_id.id
        version_domain = Domain([
            ('company_id', '=', company),
            ('contract_date_start', '<=', date_end),
            '|',
            ('contract_date_end', '=', False),
            ('contract_date_end', '>=', date_start),
        ])
        if structure:
            version_domain &= Domain([('structure_type_id', '=', structure.type_id.id)])
        versions = self.env['hr.version'].search(version_domain)
        domain = [('id', 'in', versions.employee_id.ids)]
        return domain

    @api.depends("structure_id")
    def _compute_schedule_pay(self):
        for payslip_run in self:
            payslip_run.schedule_pay = payslip_run.structure_id.type_id.default_schedule_pay

    @api.depends("slip_ids")
    def _compute_payslip_count(self):
        for payslip_run in self:
            payslip_run.payslip_count = len(payslip_run.slip_ids)

    @api.depends("slip_ids.state")
    def _compute_state(self):
        for payslip_run in self:
            states = payslip_run.mapped('slip_ids.state')
            if any(state == "draft" for state in states) or not payslip_run.slip_ids:
                payslip_run.state = '01_draft'
            elif any(state == "verify" for state in states):
                payslip_run.state = '02_verify'
            elif any(state == "done" for state in states):
                payslip_run.state = '03_close'
            elif any(state == "paid" for state in states):
                payslip_run.state = '04_paid'
            elif all(state == "cancel" for state in states):
                payslip_run.state = '05_cancel'
            else:
                payslip_run.state = '01_draft'

    @api.depends('schedule_pay')
    def _compute_date_start(self):
        for payslip_run in self:
            if payslip_run.schedule_pay:
                payslip_run.date_start = self.env["hr.payslip"]._schedule_period_start(payslip_run.schedule_pay, date.today(), payslip_run.country_code)

    @api.depends('date_start')
    def _compute_date_end(self):
        for payslip_run in self:
            if payslip_run.schedule_pay:
                payslip_run.date_end = (payslip_run.date_start and payslip_run.date_start +
                                        self.env["hr.payslip"]._schedule_timedelta(payslip_run.schedule_pay, payslip_run.date_start, payslip_run.country_code))

    @api.depends("slip_ids.gross_wage", "slip_ids.net_wage", "slip_ids.state")
    def _compute_gross_net_sum(self):
        for payslip_run in self:
            payslip_run.gross_sum = sum(payslip_run.slip_ids.filtered(lambda p: p.state != "cancel").mapped("gross_wage"))
            payslip_run.net_sum = sum(payslip_run.slip_ids.filtered(lambda p: p.state != "cancel").mapped("net_wage"))

    @api.model_create_multi
    def create(self, vals_list):
        formated_date_cache = {}
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = self._get_name_for_period(vals, formated_date_cache)
        return super().create(vals_list)

    def action_draft(self):
        if self.slip_ids.filtered(lambda s: s.state == 'paid'):
            raise ValidationError(self.env._('You cannot reset a pay run to draft if some of the payslips have already been paid.'))
        self.slip_ids.write({'state': 'draft'})

    def action_payment_report(self, export_format='csv'):
        self.ensure_one()
        self.env['hr.payroll.payment.report.wizard'].create([{
            'payslip_ids': self.slip_ids.ids,
            'payslip_run_id': self.id,
            'export_format': export_format
        }]).generate_payment_report()

    def action_paid(self):
        self.mapped('slip_ids').action_payslip_paid()

    def action_unpaid(self):
        self.slip_ids.action_payslip_unpaid()

    def action_validate(self):
        payslip_done_result = self.mapped('slip_ids').filtered(lambda slip: slip.state not in ['draft', 'cancel']).action_payslip_done()
        return payslip_done_result

    def action_confirm(self):
        self.slip_ids.filtered(lambda slip: slip.state == 'draft').write({'state': 'verify'})

    def action_open_payslips(self):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_payroll.action_view_hr_payslip_month_form')
        action['context'] = dict(
            literal_eval(action["context"]),
            search_default_payslip_run_id=self.id or False)
        return action

    def action_payroll_hr_employee_list_view_payrun(self, date_start=None, date_end=None, structure_id=None, company_id=None):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_payroll.action_payroll_hr_employee_list_view_payrun')
        action['domain'] = self._get_employees_domain(
            fields.Date.from_string(date_start),
            fields.Date.from_string(date_end),
            structure_id,
            company_id,
        )
        return action

    def generate_payslips(self, employee_ids):
        self.ensure_one()

        if not employee_ids:
            raise UserError(self.env._("You must select employee(s) to generate payslip(s)."))

        Payslip = self.env['hr.payslip']

        all_versions = dict(self.env['hr.version']._read_group(
            domain=[
                ('employee_id', 'in', employee_ids),
                ('company_id', '=', self.company_id.id),
                ('contract_date_start', '<=', self.date_end),
                '|',
                    ('contract_date_end', '=', False),
                    ('contract_date_end', '>=', self.date_start),
                ('date_version', '<=', self.date_end),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))

        valid_versions = self.env["hr.version"]
        for employee_versions in all_versions.values():
            employee_valid_versions = self.env["hr.version"]
            for version in employee_versions.sorted('date_version', reverse=True):
                if version.date_version <= self.date_start:
                    employee_valid_versions |= version
                    break
                if employee_valid_versions:
                    if employee_valid_versions[-1].contract_date_start > version.contract_date_start >= version.date_version:
                        employee_valid_versions |= version
                elif version.contract_date_start >= version.date_version:
                    employee_valid_versions |= version
            valid_versions |= employee_valid_versions

        if self.structure_id:
            valid_versions = valid_versions.filtered(lambda c: c.structure_type_id.id in self.structure_id.type_id.ids)
        valid_versions.generate_work_entries(self.date_start, self.date_end)

        all_work_entries = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('employee_id', 'in', employee_ids),
                ('date_start', '<=', self.date_end),
                ('date_stop', '>=', self.date_start),
            ],
            groupby=['version_id'],
            aggregates=['id:recordset'],
        ))

        utc = pytz.utc
        for tz, slips_per_tz in self.slip_ids.grouped(lambda s: s.version_id.tz).items():
            slip_tz = pytz.timezone(tz or utc)
            for slip in slips_per_tz:
                date_from = slip_tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(utc).replace(tzinfo=None)
                date_to = slip_tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(utc).replace(tzinfo=None)
                if version_work_entries := all_work_entries.get(slip.version_id):
                    version_work_entries.filtered_domain([
                        ('date_stop', '<=', date_to),
                        ('date_start', '>=', date_from),
                    ])
                    version_work_entries._check_undefined_slots(slip.date_from, slip.date_to)

        for work_entries in all_work_entries.values():
            work_entries = work_entries.filtered(lambda we: we.state != 'validated')
            if work_entries._check_if_error():
                work_entries = work_entries.filtered(lambda we: we.state == 'conflict')
                conflicts = work_entries._to_intervals()
                time_intervals_str = "".join(
                    f"\n - {start} -> {end} ({entry.employee_id.name})" for start, end, entry in conflicts._items)
                raise UserError(self.env._("Some work entries could not be validated. Time intervals to look for:%s", time_intervals_str))

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for version in valid_versions[::-1]:
            values = default_values | {
                'name': self.env._('New Payslip'),
                'employee_id': version.employee_id.id,
                'payslip_run_id': self.id,
                'date_from': self.date_start,
                'date_to': self.date_end,
                'version_id': version.id,
                'company_id': self.company_id.id,
                'struct_id': self.structure_id.id or version.structure_type_id.default_struct_id.id,
            }
            payslips_vals.append(values)
        self.slip_ids |= Payslip.with_context(tracking_disable=True).create(payslips_vals)
        self.slip_ids.compute_sheet()
        self.slip_ids.write({'state': 'verify'})
        self.state = '02_verify'

        return 1

    def add_payslips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Add Payslips'),
            'res_model': 'hr.payslip',
            'views': [[False, 'list']],
            'target': 'new',
            'context': {
                'create': 0,
                'delete': 0,
                'edit': 0,
                'add_payslips': 1,
            },
            'domain': [('payslip_run_id', '=', False)],
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(self.mapped('slip_ids').filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(self.env._("You can't delete a pay run with payslips if they are not draft or cancelled."))

    def _are_payslips_ready(self):
        return any(slip.state in ['done', 'cancel'] for slip in self.mapped('slip_ids'))

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.company.resource_calendar_id._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=pytz.utc),
            datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=pytz.utc),
            self.company_id,
        )

    def get_formview_action(self, access_uid=None):
        return self.action_open_payslips()

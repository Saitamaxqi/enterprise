# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import format_date


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
                                    required=True, compute='_compute_employee_ids', store=True, readonly=False)
    selection_mode = fields.Selection([
        ('employee', 'By Employee'),
        ('department', 'By Department'),
        ('job', 'By Job Position'),
        ('structure', 'By Salary Structure Types'),
        ('category', 'By Employee Tags')],
        string='Selection Mode', readonly=False, required=True, default='employee',
        help="Allow to select employees in batchs:\n- By Employee: for a specific employee"
             "\n- By Department: all employees of the specified department"
             "\n- By Job Position: all employees of the specified job position"
             "\n- By Salary Structure Types: all employees of the specified salary structure types"
             "\n- By Employee Tags: all employees of the specific employee group category")
    structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', compute='_compute_structure_id', readonly=False, store=True)
    structure_type_ids = fields.Many2many('hr.payroll.structure.type', string='Salary Structure Type')
    job_ids = fields.Many2many('hr.job', string='Job Position')
    department_ids = fields.Many2many('hr.department')
    select_employee_ids = fields.Many2many('hr.employee', string='Select Employees', domain="[('company_id', 'in', allowed_company_ids)]")
    category_ids = fields.Many2many('hr.employee.category', string='Employee Tag')

    def _get_employees_in_contract(self):
        employees = self.env['hr.employee'].search(self.get_employees_domain())
        payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        if payslip_run:
            return employees.filtered(lambda e: not e.date_end or e.date_end >= payslip_run.date_start)
        return employees

    @api.depends('structure_id', 'department_ids', 'structure_type_ids', 'job_ids', 'selection_mode', 'select_employee_ids', 'category_ids')
    def _compute_employee_ids(self):
        for wizard in self:
            wizard.employee_ids = self._get_employees_in_contract()

    @api.depends('structure_type_ids')
    def _compute_structure_id(self):
        for wizard in self:
            wizard.structure_id = wizard.structure_type_ids[0].default_struct_id if wizard.structure_type_ids else False

    def get_employees_domain(self):
        domain = [('company_id', '=', self.env.company.id)]
        if self.selection_mode == 'employee' and self.select_employee_ids:
            domain = expression.AND([
                domain,
                [('id', 'in', self.select_employee_ids.ids)]
            ])
        elif self.selection_mode == 'department' and self.department_ids:
            domain = expression.AND([
                domain,
                [('department_id', 'child_of', self.department_ids.ids)]
            ])
        elif self.selection_mode == 'structure' and self.structure_type_ids:
            domain = expression.AND([
                domain,
                [('version_ids.structure_type_id', 'in', self.structure_type_ids.ids)]
            ])
        elif self.selection_mode == 'job' and self.job_ids:
            domain = expression.AND([
                domain,
                [('job_id', 'in', self.job_ids.ids)]
            ])
        elif self.selection_mode == 'category' and self.category_ids:
            domain = expression.AND([
                domain,
                [('category_ids', 'in', self.category_ids.ids)]
            ])
        if self.structure_id:
            domain = expression.AND([
                domain,
                [('version_ids.structure_type_id', '=', self.structure_id.type_id.id)]
            ])
        return domain

    def _filter_versions(self, versions):
        # Could be overriden to avoid having 2 'end of the year bonus' payslips, etc.
        if self.structure_type_ids:
            versions = versions.filtered(lambda v: v.structure_type_id in self.structure_type_ids)
        if self.structure_id:
            versions = versions.filtered(lambda v: v.structure_type_id in self.structure_id.type_id)
        return versions

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.Date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %(from_date)s to %(end_date)s', from_date=format_date(self.env, from_date), end_date=format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create([{
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            }])
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }

        versions = employees._get_versions_with_contract_overlap_with_period(payslip_run.date_start, payslip_run.date_end)
        versions.generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end + relativedelta(days=1)),
            ('date_stop', '>=', payslip_run.date_start + relativedelta(days=-1)),
            ('employee_id', 'in', employees.ids),
        ])
        for slip in payslip_run.slip_ids:
            slip_tz = pytz.timezone(slip.version_id.resource_calendar_id.tz or slip.employee_id.tz or slip.company_id.resource_calendar_id.tz or 'UTC')
            utc = pytz.timezone('UTC')
            date_from = slip_tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(utc).replace(tzinfo=None)
            date_to = slip_tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(utc).replace(tzinfo=None)
            payslip_work_entries = work_entries.filtered_domain([
                ('version_id', '=', slip.version_id.id),
                ('date_stop', '<=', date_to),
                ('date_start', '>=', date_from),
            ])
            payslip_work_entries._check_undefined_slots(slip.date_from, slip.date_to)

        if self.structure_id.type_id.default_struct_id == self.structure_id:
            work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
            if work_entries._check_if_error():
                work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

                for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                    work_entries_by_contract[work_entry.version_id] |= work_entry

                for work_entries in work_entries_by_contract.values():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str = "".join(f"\n - {start} -> {end} ({entry.employee_id.name})" for start, end, entry in conflicts._items)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Some work entries could not be validated.'),
                        'message': _('Time intervals to look for:%s', time_intervals_str),
                        'sticky': False,
                    }
                }

        Payslip = self.env['hr.payslip']
        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for version in self._filter_versions(versions):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': version.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'version_id': version.id,
                'struct_id': self.structure_id.id or version.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        payslips.compute_sheet()
        payslip_run.slip_ids.write({'state': 'verify'})
        payslip_run.state = 'verify'

        return success_result

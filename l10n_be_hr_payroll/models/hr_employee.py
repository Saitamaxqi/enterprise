# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from functools import reduce

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    niss = fields.Char(
        'NISS Number', compute="_compute_niss", store=True, readonly=False,
        groups="hr.group_hr_user", tracking=True, index=True)
    spouse_fiscal_status_explanation = fields.Char(compute='_compute_spouse_fiscal_status_explanation', groups="hr.group_hr_user")

    start_notice_period = fields.Date("Start notice period", groups="hr.group_hr_user", copy=False, tracking=True)
    end_notice_period = fields.Date("End notice period", groups="hr.group_hr_user", copy=False, tracking=True)
    first_contract_in_company = fields.Date("First contract in company", groups="hr.group_hr_user", copy=False)

    certificate = fields.Selection(selection_add=[('civil_engineer', 'Master: Civil Engineering')])
    l10n_be_scale_seniority = fields.Integer(string="Seniority at Hiring", groups="hr.group_hr_user", tracking=True)

    # The attestation for the year of the first contract date
    first_contract_year_n = fields.Char(compute='_compute_first_contract_year', groups="hr_payroll.group_hr_payroll_user")
    first_contract_year_n_plus_1 = fields.Char(compute='_compute_first_contract_year', groups="hr_payroll.group_hr_payroll_user")
    l10n_be_holiday_pay_to_recover_n = fields.Float(
        string="Simple Holiday Pay to Recover (N)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer to recover.")
    l10n_be_holiday_pay_number_of_days_n = fields.Float(
        string="Number of days to recover (N)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Number of days on which you should recover the holiday pay.")
    l10n_be_holiday_pay_recovered_n = fields.Float(
        string="Recovered Simple Holiday Pay (N)", tracking=True,
        compute='_compute_l10n_be_holiday_pay_recovered', groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer already recovered.")
    double_pay_line_n_ids = fields.Many2many(
        'l10n.be.double.pay.recovery.line', 'double_pay_n_rel' 'employee_id', 'double_pay_line_n_ids',
        compute='_compute_from_double_pay_line_ids', readonly=False,
        inverse='_inverse_double_pay_line_n_ids',
        string='Previous Occupations (N)', groups="hr_payroll.group_hr_payroll_user")

    # The attestation for the previous year of the first contract date
    first_contract_year_n1 = fields.Char(compute='_compute_first_contract_year', groups="hr_payroll.group_hr_payroll_user")
    l10n_be_holiday_pay_to_recover_n1 = fields.Float(
        string="Simple Holiday Pay to Recover (N-1)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer to recover.")
    l10n_be_holiday_pay_number_of_days_n1 = fields.Float(
        string="Number of days to recover (N-1)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Number of days on which you should recover the holiday pay.")
    l10n_be_holiday_pay_recovered_n1 = fields.Float(
        string="Recovered Simple Holiday Pay (N-1)", tracking=True,
        compute='_compute_l10n_be_holiday_pay_recovered', groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer already recovered.")
    double_pay_line_n1_ids = fields.Many2many(
        'l10n.be.double.pay.recovery.line', 'double_pay_n1_rel' 'employee_id', 'double_pay_line_n1_ids',
        compute='_compute_from_double_pay_line_ids', readonly=False,
        inverse='_inverse_double_pay_line_n1_ids',
        string='Previous Occupations (N-1)', groups="hr_payroll.group_hr_payroll_user")
    first_contract_year = fields.Integer(compute='_compute_first_contract_year', groups="hr_payroll.group_hr_payroll_user")
    double_pay_line_ids = fields.One2many(
        'l10n.be.double.pay.recovery.line', 'employee_id',
        string='Previous Occupations', groups="hr_payroll.group_hr_payroll_user")

    @api.depends('version_ids.date_version', 'version_ids.contract_date_start', 'version_ids.contract_date_end')
    def _compute_first_contract_year(self):
        for employee in self:
            version_date = employee._get_first_version_date()
            year = (version_date or fields.Date.today()).year
            employee.first_contract_year = year
            employee.first_contract_year_n = year
            employee.first_contract_year_n1 = year - 1
            employee.first_contract_year_n_plus_1 = year + 1

    def _compute_from_double_pay_line_ids(self):
        for employee in self:
            year = employee.first_contract_year
            employee.double_pay_line_n_ids = employee.double_pay_line_ids.filtered(lambda d: d.year == year)
            employee.double_pay_line_n1_ids = employee.double_pay_line_ids.filtered(lambda d: d.year == year - 1)

    def _inverse_double_pay_line_n_ids(self):
        for employee in self:
            year = employee.first_contract_year
            to_be_deleted = employee.double_pay_line_ids.filtered(lambda d: d.year == year) - employee.double_pay_line_n_ids
            employee.double_pay_line_ids.filtered(lambda d: d.id in to_be_deleted.ids).unlink()
            employee.double_pay_line_ids |= employee.double_pay_line_n_ids

    def _inverse_double_pay_line_n1_ids(self):
        for employee in self:
            year = employee.first_contract_year
            to_be_deleted = employee.double_pay_line_ids.filtered(lambda d: d.year == year - 1) - employee.double_pay_line_n1_ids
            employee.double_pay_line_ids.filtered(lambda d: d.id in to_be_deleted.ids).unlink()
            employee.double_pay_line_ids |= employee.double_pay_line_n1_ids

    @api.constrains('start_notice_period', 'end_notice_period')
    def _check_notice_period(self):
        for employee in self:
            if employee.start_notice_period and employee.end_notice_period and employee.start_notice_period > employee.end_notice_period:
                raise ValidationError(_('The employee start notice period should be set before the end notice period'))

    def _compute_l10n_be_holiday_pay_recovered(self):
        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', self.ids),
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id),
            ('company_id', '=', self.env.company.id),
            ('state', 'in', ['done', 'paid']),
        ])
        line_values = payslips._get_line_values(['HolPayRecN', 'HolPayRecN1'])
        payslips_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in payslips:
            payslips_by_employee[payslip.employee_id] |= payslip

        for employee in self:
            employee_payslips = payslips_by_employee[employee]
            employee.l10n_be_holiday_pay_recovered_n = - sum(line_values['HolPayRecN'][p.id]['total'] for p in employee_payslips)
            employee.l10n_be_holiday_pay_recovered_n1 = - sum(line_values['HolPayRecN1'][p.id]['total'] for p in employee_payslips)

    def _compute_spouse_fiscal_status_explanation(self):
        no_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_no_income_threshold')
        low_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_low_income_threshold')
        other_income_threshold = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('spouse_other_income_threshold')
        for employee in self:
            employee.spouse_fiscal_status_explanation = _("""- High Income: Spouse earns more than %(low_income_threshold)s€ net/month.\n
- Low Income: Spouse earns between %(no_income_threshold)s€ and %(low_income_threshold)s€ net/month.\n
- Without Income: Spouse earns less than %(no_income_threshold)s€ net/month.\n
- High Pensions : Spouse is eligible to a pension higher than %(other_income_threshold)s€ net/month.\n
- Low Pensions : Spouse is eligible to a pension lower than %(other_income_threshold)s€ net/month.\n
Earnings are made of professional income, remuneration, unemployment allocations, annuities or similar income.""",
        no_income_threshold=no_income_threshold,
        low_income_threshold=low_income_threshold,
        other_income_threshold=other_income_threshold)

    @api.depends('identification_id')
    def _compute_niss(self):
        characters = dict.fromkeys([',', '.', '-', ' '], '')
        for employee in self:
            if employee.identification_id and not employee.niss and employee.company_country_code == 'BE':
                employee.niss = reduce(lambda a, kv: a.replace(*kv), characters.items(), employee.identification_id)

    @api.model
    def _validate_niss(self, niss):
        try:
            test = niss[:-2]
            if test[0] in ['0', '1', '2', '3', '4', '5']:  # Should be good for several years
                test = '2%s' % test
            checksum = int(niss[-2:])
            if checksum != (97 - int(test) % 97):
                raise Exception()
            return True
        except Exception:
            return False

    def _is_niss_valid(self):
        # The last 2 positions constitute the check digit. This check digit is
        # a sequence of 2 digits forming a number between 01 and 97. This number is equal to 97
        # minus the remainder of the division by 97 of the number formed:
        # - either by the first 9 digits of the national number for people born before the 1st
        # January 2000.
        # - either by the number 2 followed by the first 9 digits of the national number for people
        # born after December 31, 1999.
        # (https://fr.wikipedia.org/wiki/Num%C3%A9ro_de_registre_national)
        self.ensure_one()
        niss = self.niss
        if not niss or len(niss) != 11:
            return False
        return self._validate_niss(niss)

    @api.onchange('disabled_children_bool')
    def _onchange_disabled_children_bool(self):
        self.disabled_children_number = 0

    @api.onchange('other_dependent_people')
    def _onchange_other_dependent_people(self):
        self.other_senior_dependent = 0.0
        self.other_disabled_senior_dependent = 0.0
        self.other_juniors_dependent = 0.0
        self.other_disabled_juniors_dependent = 0.0

    @api.model
    def _get_invalid_niss_employee_ids(self):
        res = self.search_read([
            ('company_id', 'in', self.env.companies.filtered(lambda c: c.country_id.code == 'BE').ids),
            ('employee_type', 'in', ('employee', 'student')),
        ], ['id', 'niss'])
        return [row['id'] for row in res if not row['niss'] or not self._validate_niss(row['niss'])]

    def _get_first_versions(self):
        self.ensure_one()
        versions = super()._get_first_versions()
        pfi = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_pfi', raise_if_not_found=False)
        if not pfi:
            return versions
        return versions.filtered(
            lambda c: c.company_id.country_id.code != 'BE' or (c.company_id.country_id.code == 'BE' and c.contract_type_id != pfi))

    def write(self, vals):
        res = super().write(vals)
        if vals.get('current_version_id'):
            self.current_version_id.filtered('contract_date_start')._trigger_l10n_be_next_activities()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees.current_version_id.filtered('contract_date_start')._trigger_l10n_be_next_activities()
        return employees

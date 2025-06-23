# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import single_email_re

auto_mobile_re = re.compile(r"^\+\d{1,3}-\d{1,29}$")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_hk_surname = fields.Char(
        string="Surname",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_given_name = fields.Char(
        string="Given Name",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_name_in_chinese = fields.Char(
        string="Name in Chinese",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_passport_place_of_issue = fields.Char(
        string="Place of Issue",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_spouse_identification_id = fields.Char(
        string="Spouse Identification No",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_spouse_passport_id = fields.Char(
        string="Spouse Passport No",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_spouse_passport_place_of_issue = fields.Char(
        string="Spouse Place of Issue",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_mpf_manulife_account = fields.Char(
        string="MPF Manulife Account",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False,
    )
    l10n_hk_rental_ids = fields.One2many(
        comodel_name='l10n_hk.rental',
        inverse_name='employee_id',
        string='Rentals',
        copy=False,
        groups="hr.group_hr_user",
    )
    l10n_hk_rentals_count = fields.Integer(
        compute='_compute_l10n_hk_rentals_count',
        groups="hr.group_hr_user",
    )
    l10n_hk_years_of_service = fields.Float(
        string="Years of Service",
        compute="_compute_l10n_hk_years_of_service",
        digits=(16, 2),
        groups="hr.group_hr_user",
    )

    # Autopay fields
    l10n_hk_autopay_account_type = fields.Selection(
        selection=[
            ('bban', 'Bank Code + Account Number + Beneficiary Name'),
            ('svid', 'FPS ID'),
            ('emal', 'Email address + / Bank Code'),
            ('mobn', '(Country Code) Mobile Phone Number + / Bank Code'),
            ('hkid', 'HKID + Beneficiary Name'),
        ],
        default='bban',
        string='Autopay Payment Type',
        groups='hr.group_hr_user',
    )
    l10n_hk_autopay_svid = fields.Char(string='FPS Identifier', groups="hr.group_hr_user")
    l10n_hk_autopay_email = fields.Char(string='Autopay Email Address', groups="hr.group_hr_user")
    l10n_hk_autopay_mobile = fields.Char(string='Autopay Mobile Number', groups="hr.group_hr_user")
    l10n_hk_autopay_ref = fields.Char(string='Autopay Reference', groups="hr.group_hr_user")

    l10n_hk_internet = fields.Monetary(readonly=False, related="version_id.l10n_hk_internet", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_hk_mpf_vc_option = fields.Selection(readonly=False, related="version_id.l10n_hk_mpf_vc_option", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_hk_mpf_vc_percentage = fields.Float(readonly=False, related="version_id.l10n_hk_mpf_vc_percentage", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_hk_rental_id = fields.Many2one(readonly=False, related="version_id.l10n_hk_rental_id", inherited=True, groups="hr_payroll.group_hr_payroll_user")

    @api.constrains('l10n_hk_autopay_email')
    def _check_l10n_hk_autopay_email(self):
        for employee in self:
            if employee.l10n_hk_autopay_email and not single_email_re.match(employee.l10n_hk_autopay_email):
                raise ValidationError(employee.env._('The "Autopay Email Address" field must be filled with a single correct email address.'))

    @api.constrains('l10n_hk_autopay_mobile')
    def _check_l10n_hk_auto_mobile(self):
        for employee in self:
            if employee.l10n_hk_autopay_mobile and not auto_mobile_re.match(employee.l10n_hk_autopay_mobile):
                raise ValidationError(employee.env._('The "Autopay Mobile Number" must match the format "+xxx-xxxxxxxx".'))

    @api.depends('l10n_hk_surname', 'l10n_hk_given_name')
    def _compute_legal_name(self):
        hk_employees = self.filtered(lambda e: e.company_id.country_code == 'HK' and (e.l10n_hk_surname or e.l10n_hk_given_name))
        for employee in hk_employees:
            employee.legal_name = ' '.join(filter(None, [employee.l10n_hk_surname, employee.l10n_hk_given_name]))

        super(HrEmployee, self - hk_employees)._compute_legal_name()

    @api.depends('version_ids', 'contract_date_start')
    def _compute_l10n_hk_years_of_service(self):
        for employee in self:
            contracts = employee.version_ids.sorted('date_start', reverse=True)
            if contracts:
                contract_end_date = contracts[0].date_end or fields.Date.today()
                employee.l10n_hk_years_of_service = ((contract_end_date - employee.contract_date_start).days + 1) / 365

    @api.depends('l10n_hk_rental_ids')
    def _compute_l10n_hk_rentals_count(self):
        for employee in self:
            employee.l10n_hk_rentals_count = len(employee.l10n_hk_rental_ids)

    def action_open_rentals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('l10n_hk_hr_payroll.action_l10n_hk_rental')
        action['views'] = [(False, 'list'), (False, 'form')]
        action['domain'] = [('id', 'in', self.l10n_hk_rental_ids.ids)]
        action['context'] = {'default_employee_id': self.id}
        return action

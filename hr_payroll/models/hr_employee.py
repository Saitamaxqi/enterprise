# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    currency_id = fields.Many2one(
        "res.currency",
        string='Currency',
        related='company_id.currency_id')
    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True, groups="hr_payroll.group_hr_payroll_user")
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count', groups="hr_payroll.group_hr_payroll_user")
    registration_number = fields.Char('Employee Reference', groups="hr.group_hr_user", copy=False)
    salary_attachment_ids = fields.Many2many(
        'hr.salary.attachment',
        string='Salary Attachments',
        groups="hr_payroll.group_hr_payroll_user")
    salary_attachment_count = fields.Integer(
        compute='_compute_salary_attachment_count', string="Salary Attachment Count",
        groups="hr_payroll.group_hr_payroll_user")
    mobile_invoice = fields.Binary(string="Mobile Subscription Invoice", groups="hr.group_hr_manager")
    sim_card = fields.Binary(string="SIM Card Copy", groups="hr.group_hr_manager")
    internet_invoice = fields.Binary(string="Internet Subscription Invoice", groups="hr.group_hr_manager")

    _unique_registration_number = models.Constraint(
        'UNIQUE(registration_number, company_id)',
        "No duplication of registration numbers is allowed",
    )

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)

    def _compute_salary_attachment_count(self):
        for employee in self:
            employee.salary_attachment_count = len(employee.salary_attachment_ids)

    def action_open_payslips(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_view_hr_payslip_month_form")
        action.update({
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'search_default_group_by_version_id': 1,
                'default_employee_id': self.id,
            },
        })
        return action

    def action_open_salary_attachments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.hr_salary_attachment_action")
        action.update({'domain': [('employee_ids', 'in', self.ids)],
                       'context': {'default_employee_ids': self.ids}})
        return action

    @api.model
    def _get_account_holder_employees_data(self):
        # as acc_type isn't stored we can not use a domain to retrieve the employees
        # bypass orm for performance, we only care about the employee id anyway

        # return nothing if user has no right to either employee or bank partner
        if (not self.browse().has_access('read') or
                not self.env['res.partner.bank'].has_access('read')):
            return []

        # [XBO] TODO: to check the query before we filtered to only get the employee with running contract.
        # Maybe using current_version_id?
        self.env.cr.execute('''
            SELECT emp.id,
                   acc.acc_number,
                   acc.allow_out_payment
              FROM hr_employee emp
         LEFT JOIN res_partner_bank acc
                ON acc.id=emp.bank_account_id
              JOIN hr_version ver
                ON ver.employee_id=emp.id
             WHERE emp.company_id IN %s
               AND emp.active=TRUE
               AND emp.bank_account_id is not NULL
        ''', (tuple(self.env.companies.ids),))

        return self.env.cr.dictfetchall()

    def _get_untrusted_bank_employee_ids(self, employees_data=False):
        if not employees_data:
            employees_data = self._get_account_holder_employees_data()
        return [employee['id'] for employee in employees_data if not employee['allow_out_payment']]

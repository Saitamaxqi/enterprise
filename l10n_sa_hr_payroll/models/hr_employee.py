# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_sa_employee_code = fields.Char(string="Saudi National / IQAMA ID", groups="hr_payroll.group_hr_payroll_user")
    l10n_sa_remaining_annual_leave_balance = fields.Float(compute="_compute_l10n_sa_remaining_annual_leave_balance",
        groups="hr.group_hr_user")

    def _compute_l10n_sa_remaining_annual_leave_balance(self):
        emp_per_company = self.grouped('company_id')
        annual_leave_type_allocation_data = ({
            company.id: company.l10n_sa_annual_leave_type_id.get_allocation_data(emp_per_company[company])
                for company in self.company_id
                if company.l10n_sa_annual_leave_type_id
        })
        for employee in self:
            company_data = annual_leave_type_allocation_data.get(employee.company_id.id, {})
            employee_allocation_data = company_data.get(employee, False)
            employee.l10n_sa_remaining_annual_leave_balance = employee_allocation_data[0][1]['remaining_leaves'] \
                if employee_allocation_data else 0

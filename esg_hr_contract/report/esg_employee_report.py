import statistics

from odoo import api, fields, models


class EsgEmployeeReport(models.Model):
    _inherit = "esg.employee.report"

    wage = fields.Float("Wage", aggregator="avg", readonly=True, groups="hr_contract.group_hr_contract_employee_manager")
    job_id = fields.Many2one("hr.job", string="Job Position", readonly=True, groups="hr_contract.group_hr_contract_employee_manager")
    contract_type_id = fields.Many2one("hr.contract.type", string="Contract Type", readonly=True, groups="hr_contract.group_hr_contract_employee_manager")

    def _select(self):
        return super()._select() + """,
            hc.wage,
            hc.job_id,
            hc.contract_type_id
        """

    def _from(self):
        return super()._from() + """
            LEFT JOIN hr_contract hc ON e.contract_id = hc.id
        """

    def _group_by(self):
        return super()._group_by() + """,
            hc.wage,
            hc.job_id,
            hc.contract_type_id
        """

    @api.model
    def get_overall_pay_gap(self):
        if not self.env.user.has_group("hr_contract.group_hr_contract_employee_manager"):
            return None
        emp_by_gender = dict(self.env["hr.employee"]._read_group(
            domain=[("company_id", "in", self.env.companies.ids)],
            groupby=["gender"],
            aggregates=["id:recordset"],
        ))
        male_employees = emp_by_gender.get("male", self.env["hr.employee"])
        female_employees = emp_by_gender.get("female", self.env["hr.employee"])

        # Normalize wages to a hourly wage
        def get_wages(employees):
            wages = []
            for emp in employees:
                if wage := emp.contract_id._get_normalized_wage():
                    wages.append(wage)
            return wages

        male_wages = get_wages(male_employees)
        female_wages = get_wages(female_employees)

        male_median = statistics.median(male_wages) if male_wages else 0
        female_median = statistics.median(female_wages) if female_wages else 0

        if not male_median or not female_median:
            return False

        return round((male_median - female_median) / male_median * 100, 2)

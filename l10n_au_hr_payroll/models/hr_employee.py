# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_au_abn = fields.Char(
        string="Australian Business Number",
        compute="_compute_l10n_au_abn",
        inverse="_inverse_l10n_au_abn",
        store=True,
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
    l10n_au_previous_payroll_id = fields.Char(
        string="Previous Payroll ID",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_au_payroll_id = fields.Char(
        string="Payroll ID",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_au_medicare_variation_form = fields.Binary(string="Medicare Variation Form", attachment=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_medicare_variation_form_filename = fields.Char(groups="hr_payroll.group_hr_payroll_user")
    l10n_au_super_account_ids = fields.One2many(
        "l10n_au.super.account",
        "employee_id",
        string="Super Accounts",
        groups="hr_payroll.group_hr_payroll_user",
    )
    super_account_warning = fields.Text(compute="_compute_proportion_warnings", groups="hr_payroll.group_hr_payroll_user")
    l10n_au_other_names = fields.Char("Other Given Names", groups="hr.group_hr_user")

    l10n_au_tfn_declaration = fields.Selection(readonly=False, related="version_id.l10n_au_tfn_declaration", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tfn = fields.Char(readonly=False, related="version_id.l10n_au_tfn", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_nat_3093_amount = fields.Float(readonly=False, related="version_id.l10n_au_nat_3093_amount", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_extra_pay = fields.Boolean(readonly=False, related="version_id.l10n_au_extra_pay", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_training_loan = fields.Boolean(readonly=False, related="version_id.l10n_au_training_loan", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_medicare_exemption = fields.Selection(readonly=False, related="version_id.l10n_au_medicare_exemption", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_medicare_surcharge = fields.Selection(readonly=False, related="version_id.l10n_au_medicare_surcharge", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_medicare_reduction = fields.Selection(readonly=False, related="version_id.l10n_au_medicare_reduction", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tax_free_threshold = fields.Boolean(readonly=False, related="version_id.l10n_au_tax_free_threshold", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_child_support_deduction = fields.Float(readonly=False, related="version_id.l10n_au_child_support_deduction", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_child_support_garnishee_amount = fields.Float(readonly=False, related="version_id.l10n_au_child_support_garnishee_amount", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_employment_basis_code = fields.Selection(readonly=False, related="version_id.l10n_au_employment_basis_code", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tax_treatment_category = fields.Selection(readonly=False, related="version_id.l10n_au_tax_treatment_category", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_income_stream_type = fields.Selection(readonly=False, related="version_id.l10n_au_income_stream_type", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tax_treatment_option_actor = fields.Selection(readonly=False, related="version_id.l10n_au_tax_treatment_option_actor", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_less_than_3_performance = fields.Boolean(readonly=False, related="version_id.l10n_au_less_than_3_performance", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tax_treatment_option_voluntary = fields.Selection(readonly=False, related="version_id.l10n_au_tax_treatment_option_voluntary", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tax_treatment_option_seniors = fields.Selection(readonly=False, related="version_id.l10n_au_tax_treatment_option_seniors", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_comissioners_installment_rate = fields.Float(readonly=False, related="version_id.l10n_au_comissioners_installment_rate", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_tax_treatment_code = fields.Char(readonly=False, related="version_id.l10n_au_tax_treatment_code", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_work_country_id = fields.Many2one(readonly=False, related="version_id.l10n_au_work_country_id", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_withholding_variation = fields.Selection(readonly=False, related="version_id.l10n_au_withholding_variation", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_withholding_variation_amount = fields.Float(readonly=False, related="version_id.l10n_au_withholding_variation_amount", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_additional_withholding_amount = fields.Monetary(readonly=False, related="version_id.l10n_au_additional_withholding_amount", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_casual_loading = fields.Float(readonly=False, related="version_id.l10n_au_casual_loading", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_pay_day = fields.Selection(readonly=False, related="version_id.l10n_au_pay_day", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_eligible_for_leave_loading = fields.Boolean(readonly=False, related="version_id.l10n_au_eligible_for_leave_loading", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_leave_loading = fields.Selection(readonly=False, related="version_id.l10n_au_leave_loading", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_leave_loading_leave_types = fields.Many2many(readonly=False, related="version_id.l10n_au_leave_loading_leave_types", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_leave_loading_rate = fields.Float(readonly=False, related="version_id.l10n_au_leave_loading_rate", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_cessation_type_code = fields.Selection(readonly=False, related="version_id.l10n_au_cessation_type_code", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_performances_per_week = fields.Integer(readonly=False, related="version_id.l10n_au_performances_per_week", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_workplace_giving = fields.Float(readonly=False, related="version_id.l10n_au_workplace_giving", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_workplace_giving_employer = fields.Float(readonly=False, related="version_id.l10n_au_workplace_giving_employer", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_salary_sacrifice_superannuation = fields.Float(readonly=False, related="version_id.l10n_au_salary_sacrifice_superannuation", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_salary_sacrifice_other = fields.Float(readonly=False, related="version_id.l10n_au_salary_sacrifice_other", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_extra_negotiated_super = fields.Float(readonly=False, related="version_id.l10n_au_extra_negotiated_super", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_extra_compulsory_super = fields.Float(readonly=False, related="version_id.l10n_au_extra_compulsory_super", inherited=True, groups="hr_payroll.group_hr_payroll_user")
    l10n_au_yearly_wage = fields.Monetary(readonly=False, related="version_id.l10n_au_yearly_wage", inherited=True, groups="hr_payroll.group_hr_payroll_user")

    @api.depends("l10n_au_tfn", "l10n_au_income_stream_type")
    def _compute_l10n_au_abn(self):
        for employee in self:
            if employee.l10n_au_tfn and employee.l10n_au_income_stream_type != "VOL":
                employee.l10n_au_abn = ""

    def _inverse_l10n_au_abn(self):
        for employee in self:
            if employee.l10n_au_abn and employee.l10n_au_tfn_declaration != "000000000" and employee.l10n_au_income_stream_type != "VOL":
                employee.l10n_au_tfn = ""

    def _get_active_super_accounts(self):
        """Get all available super accounts active during a payment cycle with some
        proportion assigned.

        Returns:
            l10n_au.super.account: Returns a Recordset of super accounts sorted by proportion
        """
        self.ensure_one()
        return self.l10n_au_super_account_ids\
            .filtered(lambda account: account.account_active and account.proportion > 0)\
            .sorted('proportion')

    @api.depends(
        "l10n_au_super_account_ids",
        "l10n_au_super_account_ids.proportion",
        "l10n_au_super_account_ids.account_active",
    )
    def _compute_proportion_warnings(self):
        proportions = dict(self.env["l10n_au.super.account"]._read_group(
            [("employee_id", "in", self.ids), ("account_active", "=", True)],
            ["employee_id"],
            ["proportion:sum"],
        ))
        self.super_account_warning = False
        for emp in self:
            if proportions.get(emp) and float_compare(proportions.get(emp), 1, precision_digits=2) != 0:
                emp.super_account_warning = _(
                    "The proportions of super contributions for this employee do not amount to 100%% across their "
                    "active super accounts! Currently, it is at %d%%!",
                    proportions[emp.id] * 100,
                )

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
        groups="hr.group_hr_user")
    l10n_au_previous_payroll_id = fields.Char(
        string="Previous Payroll ID",
        groups="hr.group_hr_user")
    l10n_au_payroll_id = fields.Char(
        string="Payroll ID",
        groups="hr.group_hr_user")
    l10n_au_medicare_variation_form = fields.Binary(string="Medicare Variation Form", attachment=True, groups="hr.group_hr_user")
    l10n_au_medicare_variation_form_filename = fields.Char(groups="hr.group_hr_user")
    l10n_au_super_account_ids = fields.One2many(
        "l10n_au.super.account",
        "employee_id",
        string="Super Accounts",
        groups="hr.group_hr_user",
    )
    super_account_warning = fields.Text(compute="_compute_proportion_warnings", groups="hr.group_hr_user")
    l10n_au_other_names = fields.Char("Other Given Names", groups="hr.group_hr_user")

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

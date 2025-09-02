# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResGroups(models.Model):
    _name = "res.groups"
    _inherit = ["res.groups", "l10n_au.audit.logging.mixin"]

    def _l10n_au_get_privileged_groups(self):
        """ Returns a list of privileged groups for security checks and logging.
            This includes all the accounting, payroll, and system groups.
        """
        privileges = (
            # Accounting
            self.env.ref("account.res_groups_privilege_accounting")
            + self.env.ref("account.res_group_privilege_accounting_bank")
            # Payroll
            + self.env.ref("hr.res_groups_privilege_employees")
            + self.env.ref("hr_payroll.res_groups_privilege_payroll")
            + self.env.ref("hr_holidays.res_groups_privilege_time_off")
            + (
                self.env.ref("hr_expense.res_groups_privilege_expenses", raise_if_not_found=False)
                or self.env["res.groups.privilege"].browse()
            )  # If hr_expense installed
        )

        return self.env["res.groups"].search([("privilege_id", "in", privileges.ids)]) + self.env.ref("base.group_system")

    def _records_to_log(self):
        groups = self._l10n_au_get_privileged_groups()
        return self.filtered(lambda r: r in groups)

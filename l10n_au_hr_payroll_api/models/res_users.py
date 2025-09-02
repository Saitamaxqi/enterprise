# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResUsers(models.Model):
    _name = "res.users"
    _inherit = ["l10n_au.audit.logging.mixin", "res.users"]
    # Force the mixin to be at the bottom to pass context to prevent
    # duplications due to group_ids

    @api.model
    def _get_display_name_fields(self):
        return ["name"]

    @api.model
    def _get_audit_logging_fields(self):
        return ["password", "company_ids"]

    def _records_to_log(self):
        return self.filtered(lambda r: "AU" in r.mapped("company_ids.country_code"))

    def _is_privileged_australian_user(self):
        """Check if the user is a privileged user for Australian Payroll."""
        self.ensure_one()
        sudo_self = self.sudo()
        if "AU" not in sudo_self.company_ids.mapped("country_code"):
            return False
        return self in sudo_self.env["res.groups"]._l10n_au_get_privileged_groups().user_ids

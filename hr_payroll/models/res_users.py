# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_personal_info_partner_ids_to_notify(self, employee):
        if employee.version_id.hr_responsible_id:
            return (
                _("You are receiving this message because you are the HR Responsible of this employee."),
                employee.version_id.hr_responsible_id.partner_id.ids,
            )
        return ('', [])

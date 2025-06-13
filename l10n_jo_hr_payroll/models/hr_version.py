# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrVersion(models.Model):
    _inherit = 'hr.version'

    l10n_jo_housing_allowance = fields.Monetary(string='Jordan Housing Allowance', groups="hr.group_hr_user")
    l10n_jo_transportation_allowance = fields.Monetary(string='Jordan Transportation Allowance', groups="hr.group_hr_user")
    l10n_jo_other_allowances = fields.Monetary(string='Jordan Other Allowances', groups="hr.group_hr_user")
    l10n_jo_tax_exemption = fields.Monetary(string='Jordan Tax Exemption Amount', groups="hr.group_hr_user")

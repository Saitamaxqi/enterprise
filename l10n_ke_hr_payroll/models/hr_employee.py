from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ke_kra_pin = fields.Char(string="KRA PIN", help="KRA PIN provided by the KRA", groups="hr.group_hr_user")
    l10n_ke_nssf_number = fields.Char(string="NSSF Number", help="NSSF Number provided by the NSSF", groups="hr.group_hr_user")
    l10n_ke_nhif_number = fields.Char("NHIF Number", groups="hr.group_hr_user")
    l10n_ke_shif_number = fields.Char("SHIF Number", groups="hr.group_hr_user")
    l10n_ke_pin = fields.Char(string="Employee's PIN", groups="hr.group_hr_user")
    l10n_ke_helb_number = fields.Char(string="HELB Number", groups="hr.group_hr_user")

from odoo import fields, models


class HrVersion(models.Model):
    """
    Employee contract allows to add different values in fields.
    Fields are used in salary rule computation.
    """
    _inherit = 'hr.version'

    l10n_in_tds = fields.Float(string='TDS', digits='Payroll', groups="hr.group_hr_user",
        help='The TDS calculator can calculate the TDS amount when at least one payslip is available. Alternatively, you can enter the amount manually')
    l10n_in_driver_salay = fields.Boolean(string='Driver Salary', groups="hr.group_hr_user",
        help='Check this box if you provide allowance for driver')
    l10n_in_medical_insurance = fields.Float(string='Medical Insurance', digits='Payroll', groups="hr.group_hr_user",
        help='Deduction towards company provided medical insurance')
    l10n_in_provident_fund = fields.Boolean(string='Provident Fund', default=False, groups="hr.group_hr_user",
        help='Check this box if you contribute for PF')
    l10n_in_voluntary_provident_fund = fields.Float(string='Voluntary Provident Fund (%)', digits='Payroll', groups="hr.group_hr_user",
        help='VPF is a safe option wherein you can contribute more than the PF ceiling of 12% that has been mandated by the government and VPF computed as percentage(%)')
    l10n_in_house_rent_allowance_metro_nonmetro = fields.Float(string='House Rent Allowance (%)', digits='Payroll', groups="hr.group_hr_user",
        help='HRA is an allowance given by the employer to the employee for taking care of his rental or accommodation expenses for metro city it is 50% and for non metro 40%. \nHRA computed as percentage(%)')
    l10n_in_supplementary_allowance = fields.Float(string='Supplementary Allowance', digits='Payroll', groups="hr.group_hr_user")
    l10n_in_gratuity = fields.Float(string='Gratuity', groups="hr.group_hr_user")
    l10n_in_esic_amount = fields.Float(string='ESIC Amount', digits='Payroll', groups="hr.group_hr_user",
        help='Deduction towards company provided ESIC Amount')
    l10n_in_leave_allowance = fields.Float(string='Leave Allowance', digits='Payroll', groups="hr.group_hr_user",
        help='Deduction towards company provided Leave Allowance')
    l10n_in_residing_child_hostel = fields.Integer("Child Residing in hostel", groups="hr.group_hr_user", tracking=True)

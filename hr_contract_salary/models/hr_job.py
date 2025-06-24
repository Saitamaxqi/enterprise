# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrJob(models.Model):
    _inherit = 'hr.job'

    contract_template_id = fields.Many2one('hr.version', domain="[('company_id', '=', company_id), ('employee_id', '=', False)]", string="Contract Template",
        help="Default contract used to generate an offer. If empty, benefits will be taken from current contract of the employee/nothing for an applicant.")
    company_id = fields.Many2one(compute='_compute_company_id', readonly=False, store=True, precompute=True)

    @api.depends('contract_template_id.company_id')
    def _compute_company_id(self):
        for job in self:
            if job.contract_template_id:
                job.company_id = job.contract_template_id.company_id

    @api.constrains('contract_template_id', 'company_id')
    def _check_contract_template_company(self):
        for job in self:
            if job.contract_template_id and job.contract_template_id.company_id != job.company_id:
                raise ValidationError(self.env._("The contract template's company must match the job's company."))

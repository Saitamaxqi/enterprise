# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_hr_payslips_tags = fields.Many2many(
        'documents.tag', 'payslip_tags_table')

    def _generate_employee_documents_folders(self):
        """ Override from documents_hr module to add payslips related tags and permissions on the
        employee document folder of each company. """
        folders = super()._generate_employee_documents_folders()
        group_payroll_user = self.env.ref('hr_payroll.group_hr_payroll_user')
        payslip_tag = self.env.ref('documents_hr_payroll.documents_tag_payslips', raise_if_not_found=False)
        for company, folder in zip(self, folders):
            company.sudo().write({
                'documents_hr_payslips_tags': [(6, 0, payslip_tag.ids)] if payslip_tag else [],
            })
            payroll_users = group_payroll_user.all_user_ids.filtered(lambda user: folder.company_id in user.company_ids)
            folder.sudo().action_update_access_rights(
                access_internal='none', access_via_link='none', is_access_via_link_hidden=True,
                partners={partner.id: ('edit', False) for partner in payroll_users.partner_id})
        return folders

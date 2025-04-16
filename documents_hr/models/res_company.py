# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_hr_settings = fields.Boolean(default=True)
    documents_hr_folder = fields.Many2one('documents.document', string="HR Folder", check_company=True,
                                          domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
                                          compute='_compute_documents_hr_folder', store=True, readonly=False)
    documents_employee_folder_id = fields.Many2one('documents.document', string="Employees Folder",
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)], check_company=True)
    documents_hr_contracts_tags = fields.Many2many('documents.tag', 'documents_hr_contracts_tags_table')

    @api.depends('documents_hr_settings')
    def _compute_documents_hr_folder(self):
        folder_id = self.env.ref('documents_hr.document_hr_folder', raise_if_not_found=False)
        self._reset_default_documents_folder_id('documents_hr_settings', 'documents_hr_folder', folder_id)

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [('documents_hr_folder', 'in', folder_ids), ('documents_hr_settings', '=', True)]
        ])

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._generate_employee_documents_folders()
        return companies

    def write(self, vals):
        """ Override to move all employee subfolders if the HR Employee folder has been modified in settings.
        And ensure that companies that was never configured get their employee subfolders. """
        employees_without_subfolder = self.env['hr.employee']
        if vals.get('documents_employee_folder_id'):
            employees = self.env['hr.employee'].sudo().search([('company_id', 'in', self.ids)])
            # Might be that companies was never configured and no subfolder exists for employees.
            employees_without_subfolder = employees.filtered(lambda e: not e.hr_employee_folder_id)
            employees_with_subfolders = employees - employees_without_subfolder
            if employees_with_subfolders:
                employees_with_subfolders.hr_employee_folder_id.folder_id = vals['documents_employee_folder_id']
        result = super().write(vals)
        employees_without_subfolder._generate_employee_documents_subfolders()
        return result

    def _generate_employee_documents_folders(self):
        for company in self:
            company.sudo().documents_employee_folder_id = self.env['documents.document'].sudo().create({
                'name': company.env._('Employees'),
                'type': 'folder',
                'folder_id': company.documents_hr_folder.id,
                'company_id': company.id,
                'is_access_via_link_hidden': True,
            })
        return self.mapped('documents_employee_folder_id')

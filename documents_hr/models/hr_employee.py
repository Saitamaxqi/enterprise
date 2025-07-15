# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'documents.mixin']

    document_count = fields.Integer(compute='_compute_document_count', groups="hr.group_hr_user")
    hr_employee_folder_id = fields.Many2one('documents.document', string="HR Employee Folder", groups="base.group_system,hr.group_hr_user")

    def _get_document_folder(self):
        return self.company_id.documents_hr_folder if self.company_id.documents_hr_settings else False

    def _get_document_partner(self):
        return self.work_contact_id

    def _check_create_documents(self):
        return self.company_id.documents_hr_settings and super()._check_create_documents()

    def _compute_document_count(self):
        document_count_by_folder = dict(self.env['documents.document']._read_group(
            [('folder_id', 'in', self.hr_employee_folder_id.ids)], ['folder_id'], ['__count']))
        for employee in self:
            employee.document_count = document_count_by_folder.get(employee.hr_employee_folder_id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._generate_employee_documents_subfolders()
        return employees

    def write(self, vals):
        result = super().write(vals)
        if 'name' in vals and len(self) == 1:
            # This makes no sense to rename multiple employees with the same name. This would probably be an error.
            # So we rename the folder only if one employee is renamed at a time.
            self.sudo().hr_employee_folder_id.write({'name': vals['name']})
        return result

    def action_open_documents(self):
        """ Open and display all the content of the employee subfolder under HR > Employee. """
        self.ensure_one()
        if not self.work_contact_id:
            raise ValidationError(_('You must have a contact linked to the employee in order to use Document\'s features.'))
        if not self.hr_employee_folder_id:
            raise ValidationError(_('You must configure the HR Employee folder in document settings to use Document\'s features.'))
        action = self.env['ir.actions.actions']._for_xml_id('documents.document_action_preference')
        # Documents created within that action will be 'assigned' to the employee
        # Also makes sure that the views starts on the hr_holder
        action['context'] = {
            'searchpanel_default_folder_id': self.hr_employee_folder_id.id,
            'default_res_id': self.id,
            'default_res_model': 'hr.employee',
        }
        return action

    def _generate_employee_documents_subfolders(self):
        """ Employee document folder is meant to be used by HR only to store all the documents they need regarding the
         employee (E.g.: ID Card, Drive License, etc..). The employee does not have access to this folder,
         nor the documents inside it (by default at least) """
        group_hr_user = self.env.ref('hr.group_hr_user')
        employees = self.filtered('company_id.documents_employee_folder_id')
        folders = self.env["documents.document"].sudo().create([{
            'name': employee.name,
            'type': 'folder',
            'folder_id': employee.company_id.documents_employee_folder_id.id,
            'company_id': employee.company_id.id,
        } for employee in employees])
        hr_users_per_company = {
            company: group_hr_user.all_user_ids.filtered(lambda user: company in user.company_ids)
            for company in self.company_id
        }
        for employee, folder in zip(employees, folders):
            folder.action_update_access_rights(
                access_internal='none', access_via_link='none', is_access_via_link_hidden=True,
                partners={partner.id: ('edit', False) for partner in
                          hr_users_per_company[employee.company_id].partner_id})
            employee.hr_employee_folder_id = folder.id

    def _get_employee_documents_token(self):
        self.ensure_one()
        return tools.hmac(
            self.env(su=True),
            "documents-hr-my-files",
            str(self.id),
        )

    def _get_documents_link_url(self):
        self.ensure_one()
        return f'{self.get_base_url()}/documents_hr/my_files/{self.id}/{self._get_employee_documents_token()}'

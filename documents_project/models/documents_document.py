# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo import api
from odoo.exceptions import UserError
from odoo.osv import expression


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    # for folders
    project_ids = fields.One2many('project.project', 'documents_folder_id', string="Projects")

    def _prepare_create_values(self, vals_list):
        vals_list = super()._prepare_create_values(vals_list)
        folder_ids = {folder_id for v in vals_list if (folder_id := v.get('folder_id')) and not v.get('res_id')}
        folder_id_values = {
            folder_id: self.browse(folder_id)._get_link_to_project_values()
            for folder_id in folder_ids
        }
        for vals in vals_list:
            if (folder_id := vals.get('folder_id')) and vals.get('type') != 'folder' and not vals.get('res_id'):
                vals.update({k: v for k, v in folder_id_values[folder_id].items() if k not in vals})
        return vals_list

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if (template_folder_id := self.env.context.get('project_documents_template_folder')) \
                and [('type', '=', 'folder')] in domain:
            domain = expression.AND([
                domain,
                ['!', ('id', 'child_of', template_folder_id)],
            ])
        return domain

    def _project_folder_in_self_or_ancestors(self, project_folder):
        project_folder_ancestors = {int(ancestor_id) for ancestor_id in project_folder.sudo().parent_path.split('/')[:-1]}
        return project_folder_ancestors & set(self.ids)

    @api.ondelete(at_uninstall=False)
    def unlink_except_project_folder(self):
        project_folder = self.env.ref('documents_project.document_project_folder')
        if self._project_folder_in_self_or_ancestors(project_folder):
            raise UserError(_('The "%s" workspace is required by the Project application and cannot be deleted.', project_folder.name))

    @api.constrains('company_id')
    def _check_no_company_on_projects_folder(self):
        if not self.company_id:
            return
        projects_folder = self.env.ref('documents_project.document_project_folder')
        if projects_folder in self and projects_folder.company_id:
            raise UserError(_("You cannot set a company on the %s folder.", projects_folder.name))

    @api.constrains('company_id')
    def _check_company_is_projects_company(self):
        for folder in self.filtered(lambda d: d.type == 'folder'):
            if folder.project_ids and folder.project_ids.company_id:
                different_company_projects = folder.project_ids.filtered(lambda p: p.company_id != self.company_id)
                if not different_company_projects:
                    continue
                if len(different_company_projects) == 1:
                    project = different_company_projects[0]
                    message = _('This folder should remain in the same company as the "%(project)s" project to which it is linked. Please update the company of the "%(project)s" project, or leave the company of this workspace empty.', project=project.name)
                else:
                    lines = [f"- {project.name}" for project in different_company_projects]
                    message = _('This folder should remain in the same company as the following projects to which it is linked:\n%s\n\nPlease update the company of those projects, or leave the company of this workspace empty.', '\n'.join(lines))
                raise UserError(message)

    def write(self, vals):
        write_result = super().write(vals)
        if (
            'partner_id' not in vals
            and (folder_id := vals.get('folder_id'))
            and (documents_without_partner := self.filtered(lambda d: not d.partner_id))
            and (folder_values := self.env['documents.document'].browse(folder_id)._get_link_to_project_values())
            and (partner := folder_values.get('partner_id'))
        ):
            documents_without_partner.partner_id = partner
        project_folder = self.env.ref('documents_project.document_project_folder')
        if not vals.get('active', True) and self._project_folder_in_self_or_ancestors(project_folder):
            raise UserError(_('The "%s" workspace is required by the Project application and cannot be archived.', project_folder.name))
        return write_result

    def _get_link_to_project_values(self):
        self.ensure_one()
        if self.type != 'folder' or self.shortcut_document_id:
            return {}
        if project_sudo := self._get_project_from_closest_ancestor().sudo():
            return {
                'partner_id': project_sudo.partner_id.id,
                'tag_ids': project_sudo.documents_tag_ids,
            }
        return {}

    def _get_project_from_closest_ancestor(self):
        """
        If the current folder is linked to exactly one project, this method returns
        that project.

        If the current folder doesn't match the criteria, but one of its ancestors
        does, this method will return the project linked to the closest ancestor
        matching the criteria.

        :return: The project linked to the closest valid ancestor, or an empty
        recordset if no project is found.
        """
        self.ensure_one()
        eligible_projects = self.env['project.project'].sudo()._read_group(
            [('documents_folder_id', 'parent_of', self.id)],
            ['documents_folder_id'],
            having=[('__count', '=', 1)],
        )
        if not eligible_projects:
            return self.env['project.project']

        # dict {folder_id: position}, where position is a value used to sort projects by their folder_id
        folder_id_order = {int(folder_id): i for i, folder_id in enumerate(reversed(self.parent_path[:-1].split('/')))}
        eligible_projects.sort(key=lambda project_group: folder_id_order[project_group[0].id])
        return self.env['project.project'].sudo().search(
            [('documents_folder_id', '=', eligible_projects[0][0].id)], limit=1).sudo(False)

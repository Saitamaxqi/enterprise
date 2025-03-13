# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'documents.mixin']

    def _get_document_vals_access_rights(self):
        """ All payslips should be accessible in 'Anyone with the link' to make the link permanent.
        The document must be still accessible even if the employee and its user (if any) are archived."""
        return {
            'access_via_link': 'view',
            'access_internal': 'none',
            'is_access_via_link_hidden': True,
        }

    def _get_document_access_ids(self):
        return [(self._get_document_partner(), ('view', False))]

    def _get_document_tags(self):
        return self.company_id.documents_hr_payslips_tags

    def _get_document_partner(self):
        return self.employee_id.user_id.partner_id or self.employee_id.work_contact_id

    def _get_document_owner(self):
        return self.employee_id.user_id or super()._get_document_owner()

    def _get_document_folder(self):
        return super()._get_document_folder() if self.employee_id.user_id else self.company_id._get_or_create_worker_payroll_folder()

    def _check_create_documents(self):
        return bool(self.employee_id.user_id) or self.company_id.documents_hr_settings

    def _get_email_template(self):
        return self.env.ref(
            'documents_hr_payroll.mail_template_new_payslip', raise_if_not_found=False
        ) if self._check_create_documents() else None

    def _get_document_link(self):
        self.ensure_one()
        document = self.env["documents.document"].sudo().search(
            [('res_model', '=', self._name), ('res_id', '=', self.id)],
            order='id desc',
            limit=1 # need the last one created. (if payslip [canceled and] regenerated)
        )
        return document.access_url if document else False

    @api.model
    def _cron_generate_pdf(self, batch_size=False):
        is_rescheduled = super()._cron_generate_pdf(batch_size=batch_size)
        if is_rescheduled:
            return is_rescheduled

        # Post declarations from mixin
        lines = self.env['hr.payroll.employee.declaration'].search([('pdf_to_post', '=', True)])
        if lines:
            BATCH_SIZE = batch_size or 30
            lines_batch = lines[:BATCH_SIZE]
            lines_batch._post_pdf()
            lines_batch.write({'pdf_to_post': False})
            # if necessary, retrigger the cron to generate more pdfs
            if len(lines) > BATCH_SIZE:
                self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()
                return True
        return False

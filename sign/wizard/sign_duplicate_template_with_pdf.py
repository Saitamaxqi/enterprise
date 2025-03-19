# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import base64

from odoo import api, models, fields, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.pdf import PdfFileReader, PdfReadError


class SignDuplicateTemplatePdf(models.TransientModel):
    _name = 'sign.duplicate.template.pdf'
    _description = 'Sign Duplicate Template with new PDF'

    new_pdf = fields.Binary(string="File name", required=True)
    original_template_id = fields.Many2one(
        'sign.template', string="Original File", required=True, ondelete='cascade',
        default=lambda self: self.env.context.get('active_id', None),
    )
    new_template = fields.Char('New Template Name')

    def duplicate_template_with_pdf(self):
        # Check original template access
        self.original_template_id.check_access('write')

        # Check original documents access
        for document in self.original_template_id.document_ids:
            document.check_access('write')

        # Create the new template empty documents
        new_template = self.original_template_id.sudo().copy({
            'name': self.new_template or self.original_template_id.name,
            'document_ids': [Command.set([])],
            'active': True,
            'favorited_ids': [Command.link(self.env.user.id)],
        })
        for document in self.original_template_id.document_ids.sorted('sequence'):
            if not self._compare_page_templates(document.datas, self.new_pdf):
                raise UserError(self.env._("The new PDF must have at least as many pages as the original document."))
            new_attachment = self.env['ir.attachment'].create({
                'name': f"{self.new_template or self.original_template_id.name} - {document.name}",
                'datas': self.new_pdf,
                'type': 'binary'
            })
            self.env['sign.document'].create({
                'attachment_id': new_attachment.id,
                'sequence': document.sequence,  # Preserve original sequence
                'template_id': new_template.id,
            })

        # Copy sign items while preserving document relationships
        orig_docs = self.original_template_id.document_ids.sorted('sequence')
        new_docs = new_template.document_ids.sorted('sequence')
        for orig_doc, new_doc in zip(orig_docs, new_docs):
            orig_doc._copy_sign_items_to(new_doc)

        return new_template.go_to_custom_template()

    @api.model
    def _compare_page_templates(self, original_file, new_file):
        pages_original_file = PdfFileReader(io.BytesIO(base64.b64decode(original_file)), strict=False, overwriteWarnings=False).getNumPages()
        try:
            pages_new_file = PdfFileReader(io.BytesIO(base64.b64decode(new_file)), strict=False, overwriteWarnings=False).getNumPages()
        except PdfReadError:
            raise ValidationError(_("The uploaded file is not a valid PDF. Please upload a valid PDF file."))
        return pages_new_file >= pages_original_file

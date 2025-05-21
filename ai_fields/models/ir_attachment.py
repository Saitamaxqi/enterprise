# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.ai_fields.models.models import AI_SUPPORTED_IMG_TYPES


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _ai_format(self, files_dict):
        vals = []
        for attachment in self:
            if attachment.checksum in files_dict:
                vals.append({'id': attachment.id, 'file': files_dict[attachment.checksum]['file_ref']})
                continue
            file_ref = f'<file_#{len(files_dict) + 1}>'
            extension = attachment.mimetype.split('/')[-1]
            if extension in AI_SUPPORTED_IMG_TYPES or extension == 'pdf' and not attachment.url:
                files_dict[attachment.checksum] = {
                    'type': 'pdf' if extension == 'pdf' else 'image',
                    'value': attachment.url or f"data:{attachment.mimetype};base64,{attachment.datas.decode()}",  # utf-8 ?
                    'file_ref': file_ref,
                }
            else:
                if not attachment.index_content or attachment.index_content == "application":
                    continue
                files_dict[attachment.checksum] = {
                    'type': 'text',
                    'value': attachment.index_content,
                    'file_ref': file_ref
                }
            vals.append({'id': attachment.id, 'file': file_ref})
        return vals

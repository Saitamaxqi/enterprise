# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class DocumentsTag(models.Model):
    _inherit = 'documents.tag'

    @api.model
    def _ensure_documents_account_tags_exist(self):
        tags_list = [
            {"xml_id": "documents.documents_tag_inbox", "noupdate": True, "values": {"name": "Inbox", "sequence": 4}},
            {"xml_id": "documents.documents_tag_to_validate", "noupdate": True, "values": {"name": "To validate", "sequence": 6}},
            {"xml_id": "documents.documents_tag_validated", "noupdate": True, "values": {"name": "Validated", "sequence": 8}},
            {"xml_id": "documents.documents_tag_bill", "noupdate": True, "values": {"name": "Bill", "sequence": 4}},
        ]
        self._load_records(tags_list)

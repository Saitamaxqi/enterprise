from odoo import fields
from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments


class TestDocumentsSharing(TransactionCaseDocuments):
    def test_permission_panel_access_ids_without_logs_and_owner(self):
        doc = self.env['documents.document'].create({
            'folder_id': self.folder_a.id,
            'owner_id': self.document_manager.id,
            'access_ids': False,
        })
        self.assertEqual(doc.access_ids.partner_id, self.document_manager.partner_id)
        self.env['documents.access'].create({
            'document_id': doc.id,
            'last_access_date': fields.Datetime.now(),
            'partner_id': self.internal_user.partner_id.id,
            'role': False,
        })
        doc.owner_id = False
        self.assertEqual(len(doc.access_ids), 2)
        self.assertEqual([a['partner_id']['id'] for a in doc.permission_panel_data()['record']['access_ids']],
                         [self.document_manager.partner_id.id])
        doc.owner_id = self.document_manager
        self.assertEqual(len(doc.access_ids), 2)
        self.assertEqual([a['partner_id']['id'] for a in doc.permission_panel_data()['record']['access_ids']],
                         [],
                         "Owner, and logs shouldn't be shown")

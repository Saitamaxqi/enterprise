# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest.mock

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT
from odoo.tests.common import RecordCapturer, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'documents_hr_recruitement')
class TestDocumentsMixinMulticompany(MailCommon):
    """
    Test documents creation via mail alias in a multi-company setup,
    specifically when targeting a recruitment job posting (hr.applicant)
    linked to a folder owned by a specific company.
    This tests if documents.mixin correctly handles `company_id` while getting
    the default values for document creation from a company-restricted workspace.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create Document Folder for Company B's HR Recruitment workspace
        cls.folder_hr_company_2 = cls.env['documents.document'].create({
            'name': 'HR Company 2 Documents',
            'type': 'folder',
            'company_id': cls.company_2.id,
        })

        # --- Configure Documents workspace for Recruitment ---
        # This links hr.applicant to the specific folder.
        cls.company_2.documents_recruitment_settings = True
        cls.company_2.recruitment_folder_id = cls.folder_hr_company_2.id

        # Create a Job Posting in Company 2
        cls.job_posting_company_2 = cls.env['hr.job'].with_user(cls.user_admin).create({
            'name': 'Software Developer (Company 2)',
            'company_id': cls.company_2.id,
            'user_id': cls.user_employee_c2.id,
            'alias_name': 'job-dev-company-2',
        })

        cls.email_filenames = ['attachment', 'original_msg.eml']

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_incoming_mail_to_hr_job_alias_attachment_company(self):
        """
        Test that hr.applicant and related documents created via incoming email
        to a job posting alias have the correct company_id (inherited from the
        configured recruitment workspace folder), and that no alias domain
        mismatch error occurs.
        """
        subject = "I want to work for Odoo!"
        email_from = 'jobhunter@example.com'
        email_to = f'{self.job_posting_company_2.alias_id.alias_name}@{self.mail_alias_domain_c2.name}'

        # Since Odoo 18.3, inactive aliases are not created anymore for binary attachments
        # But the fix introduced with this commit still makes sense in case of custom
        # message processing that creates folders for example
        # For now we usurp this test by mocking the method to fit our needs
        # TODO: when a proper testing module exists in the future for documents.mixin, this can
        # be recycled as need
        original_get_documents_vals = self.registry['hr.applicant']._get_document_vals

        def mocked_get_document_vals(self, attachment):
            document_vals = original_get_documents_vals(self, attachment)

            # Ad-hoc modify the document_vals dict to fit our needs (force folder creation)
            document_vals.update({
                'name': attachment.name,
                'type': 'folder',
                'attachment_id': False,
                'alias_name': attachment.name,
            })
            return document_vals

        with (
            unittest.mock.patch.object(
                self.registry['hr.applicant'],
                '_get_document_vals',
                new=mocked_get_document_vals,
                create=True,
            ),
            self.mock_mail_gateway(),
            RecordCapturer(self.env['hr.applicant'], []) as applicant_capture,
            RecordCapturer(self.env['documents.document'], []) as doc_capture,
        ):
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                email_from,
                email_to,
                subject=subject,
                target_field='display_name',  # overwrite, default is 'name', doesn't exist in hr.applicant
                target_model='hr.applicant',
                msg_id='<applicant-company-2-test@odoo.com>',
            )

        # Verify if a new applicant was created
        new_applicant = applicant_capture.records
        self.assertEqual(len(new_applicant), 1, "Should have created exactly one new applicant from the email.")

        self.assertEqual(new_applicant.company_id.id, self.company_2.id)

        # Retrieve the newly created documents associated with the new applicant
        new_documents = doc_capture.records
        self.assertEqual(set(new_documents.mapped('name')), set(self.email_filenames))
        self.assertEqual(set(new_documents.mapped('type')), {'folder'})

        self.assertEqual(new_documents.folder_id, self.folder_hr_company_2,
                         "Created folder should be in the hr folder for company 2.")
        self.assertEqual(new_documents.company_id, self.company_2,
                         "Folder company should match the hr's folder's company.")

        for doc in new_documents:
            self.assertIn(
                self.company_2,
                doc.alias_id.alias_domain_id.company_ids,
                f"Alias domain company for {doc.name} should include Company 2.",
            )

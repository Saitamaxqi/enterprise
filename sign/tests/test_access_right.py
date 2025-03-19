# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .sign_request_common import SignRequestCommon

from odoo.exceptions import AccessError


class TestAccessRight(SignRequestCommon):

    def test_update_item_partner(self):
        self.role_customer.change_authorized = True
        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2,
                                                                company=self.partner_3, cc_partners=self.partner_4)
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in
                                       sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        # We update the item partner with a non-privileged sign user.
        sign_request_item_customer.with_user(self.user_1).partner_id = self.partner_5
        # reassign
        self.assertEqual(sign_request_item_customer.signer_email, "char.aznable.a@example.com", 'email address should be char.aznable.a@example.com')

    def test_user_can_edit_only_own_templates_and_documents(self):
        """ Ensure basic sign users can only edit their own templates and documents. """
        res = self.env['sign.template'].with_user(self.user_1).create_from_attachment_data(
            attachment_data_list=[{'name': 'sample_contract.pdf', 'datas': self.pdf_data_64}]
        )
        user_1_template_id = res.get('id')
        user_1_template = self.env['sign.template'].with_user(self.user_1).browse(user_1_template_id)
        user_1_document = user_1_template.document_ids[0]
        with self.assertRaises(AccessError):
            user_1_template.with_user(self.user_2).write({'name': 'My New Name!'})
        with self.assertRaises(AccessError):
            user_1_document.with_user(self.user_2).write({'name': 'My New Name!'})

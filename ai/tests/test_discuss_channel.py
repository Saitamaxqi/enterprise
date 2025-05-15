# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import TransactionCase


class TestDiscussChannel(TransactionCase):

    def test_create_ai_chat(self):
        partner = self.env["res.partner"].create({
            "name": "Odoo AI"
        })

        channel = self.env["discuss.channel"]._get_or_create_ai_chat(partner)

        self.assertTrue(channel)
        self.assertTrue(channel.is_member, "Current user should be member of the created channel")
        self.assertEqual("ai_chat", channel.channel_type, "AI channel should be of 'ai_chat' type")
        self.assertEqual(partner.name, channel.name, "Channel of type 'ai_chat' should be named after the partner's name")

    def test_create_ai_chat_retrieves_existing_channel(self):
        partner = self.env["res.partner"].create({
            "name": "Odoo AI"
        })

        channel = self.env["discuss.channel"]._get_or_create_ai_chat(partner)
        duplicate_channel = self.env["discuss.channel"]._get_or_create_ai_chat(partner)

        self.assertEqual(channel, duplicate_channel, "Channel shouldn't be duplicated when created with the same partner.")

    def test_close_ai_chat_deletes_channel(self):
        partner = self.env["res.partner"].create({
            "name": "Odoo AI"
        })
        channel = self.env["discuss.channel"]._get_or_create_ai_chat(partner)

        channel.close_ai_chat()

        self.assertFalse(channel.exists(), "Channel of type 'ai_chat' should be deleted when closed.")

    def test_close_ai_chat_only_deletes_channel_with_proper_types(self):
        partner = self.env["res.partner"].create({
            "name": "Odoo AI"
        })
        ai_chat_channel = self.env["discuss.channel"]._get_or_create_ai_chat(partner)
        regular_channel = self.env["discuss.channel"].create({
            "channel_member_ids": [
                Command.create(
                    {
                        "partner_id": self.env.user.partner_id.id,
                    }
                ),
            ],
            "channel_type": "chat",
            "name": "Non AI chat"
        })

        ai_chat_channel.close_ai_chat()
        regular_channel.close_ai_chat()

        self.assertFalse(ai_chat_channel.exists(), "Channel of type 'ai_chat' should be deleted when closed.")
        self.assertTrue(regular_channel.exists(), "Only channels in ['ai_chat', 'ai_composer'] should be deleted on close.")

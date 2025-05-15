# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import TransactionCase


class TestAIAgent(TransactionCase):

    def test_close_chat_only_works_with_ai_channel(self):
        partner = self.env["res.partner"].create({
            "name": "Odoo AI"
        })

        agent = self.env["ai.agent"].create({
            "name": "Odoo AI",
            "partner_id": partner.id

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

        agent.close_chat(ai_chat_channel.id)
        agent.close_chat(regular_channel.id)
        self.assertFalse(ai_chat_channel.exists(), "Channel of type 'ai_chat' should be deleted when closed.")
        self.assertTrue(regular_channel.exists(), "Only channels in ['ai_chat', 'ai_composer'] should be deleted on close.")

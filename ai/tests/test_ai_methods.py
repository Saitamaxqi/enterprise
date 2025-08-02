# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAIMethods(TransactionCase):
    @patch("odoo.addons.ai.models.ai_agent.AIAgent._generate_response")
    def test_ai_methods_call_without_error(self, mock_generate_response):
        """Test that all AI rpc methods can be called without errors"""
        partner = self.env["res.partner"].create({"name": "Test AI Partner"})
        agent = self.env["ai.agent"].create({"name": "Test AI Agent", "partner_id": partner.id})
        channel = self.env["discuss.channel"]._get_or_create_ai_chat(partner)

        mock_generate_response.return_value = ["Mocked response"]

        # Test generate_response method
        mail_message = self.env["mail.message"].create(
            {
                "body": "<p>Test prompt</p>",
                "model": "discuss.channel",
                "res_id": channel.id,
            }
        )
        agent.generate_response(channel.id, mail_message)
        self.assertTrue(mock_generate_response.called)

        # Test post_error_message method
        mock_generate_response.reset_mock()
        agent.post_error_message(channel.id, "Test error message")
        self.assertTrue(mock_generate_response.called)

        # Test get_direct_response method
        mock_generate_response.reset_mock()
        result = agent.get_direct_response("Direct prompt")
        self.assertTrue(mock_generate_response.called)
        self.assertEqual(result, ["Mocked response"])

    def test_ai_agent_allow_duplicate(self):
        agent = self.env["ai.agent"].create({"name": "Test Agent"})
        agent_copy = agent.copy()
        self.assertEqual(agent_copy.name, "Test Agent (copy)")

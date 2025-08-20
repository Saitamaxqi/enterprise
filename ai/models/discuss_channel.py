# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models, api
from odoo.exceptions import AccessError

from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    """Chat Session
    Representing a conversation between users.
    It extends the base method for usage with AI assistant.
    """

    _name = "discuss.channel"
    _inherit = ["discuss.channel"]

    channel_type = fields.Selection(
        selection_add=[("ai_chat", "AI chat")],
        ondelete={"ai_chat": "cascade"},
    )
    ai_env_context = fields.Json("Context for AI agent")

    @api.model
    def create_ai_draft_channel(
        self,
        caller_component,
        channel_title,
        record_model=None,
        record_id=None,
        front_end_info=None,
        text_selection=None,
    ):
        if record_model:  # if we call the AI within a specific model, we search for composer configs that might include that model and we take the last one
            ai_composer = self.env['ai.composer'].sudo().search([
                ('interface_key', '=', caller_component),
                ('focused_models', 'in', record_model),
            ], limit=1, order="create_date DESC")
        if not ai_composer:  # if we don't find any composer configs or we call the ai from a place with no specific model, fallback to the basic composers
            ai_composer = self.env['ai.composer'].sudo().search([
                ('interface_key', '=', caller_component),
                ('focused_models', '=', False),
            ], limit=1, order="create_date DESC")
        ai_agent = ai_composer.ai_agent
        if not ai_agent:
            raise AccessError(_("AI not reachable, AI Agent not found."))

        original_record = self.env[record_model].browse(record_id)

        # create a new AI chat
        channel = ai_agent._create_ai_chat_channel(channel_name=self.env._("AI: %(name)s", name=channel_title))

        # Create the initial context for the AI - the default prompt from the composer
        model_context = [
            ai_composer.default_prompt,
        ]
        # Add extra info that are relevant to the where we call the AI from (record info, chatter info, pre-prompts, etc.)
        model_context += original_record._ai_initialise_context(
            caller_component, text_selection, front_end_info
        )
        # Finally pass the complete "save" the context to the channel
        channel.ai_env_context = model_context

        return {"ai_channel_id": channel.id, "data": Store().add(channel).get_result(), "prompts": [prompt.name for prompt in ai_composer.available_prompts]}

    def _close_older_chat_channel(self, ai_partner):
        older_channel = self.search(self._get_ai_chat_channel_domain(ai_partner))
        if older_channel:
            older_channel.sudo().unlink()

    def close_ai_chat(self):
        self.ensure_one()
        if self._should_unlink_on_close():
            self.sudo().unlink()

    def _should_unlink_on_close(self):
        return self.channel_type == "ai_chat" and self.is_member

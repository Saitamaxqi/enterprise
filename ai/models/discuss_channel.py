# Part of Odoo. See LICENSE file for full copyright and licensing details.
try:
    from markdown2 import markdown
except ImportError:
    markdown = None

from odoo import fields, models, api, Command, _
from odoo.exceptions import AccessError
from odoo.tools import SQL

from odoo.addons.iap.tools import iap_tools
from odoo.tools.mail import html_sanitize
from odoo.tools.misc import mute_logger
from odoo.addons.mail.tools.discuss import Store


DEFAULT_OLG_ENDPOINT = "https://olg.api.odoo.com"


class DiscussChannel(models.Model):
    """Chat Session
    Representing a conversation between users.
    It extends the base method for usage with AI assistant.
    """

    _name = "discuss.channel"
    _inherit = ["discuss.channel"]

    channel_type = fields.Selection(
        selection_add=[("ai_composer", "Draft with AI"), ("ai_chat", "AI chat")],
        ondelete={"ai_composer": "cascade", "ai_chat": "cascade"},
    )
    ai_context = fields.Json("Context for AI agent")
    ai_composer = fields.Many2one("ai.composer")

    def _get_composer_from_caller(self, caller):
        caller_to_composer_map = {
            "composer_ai_button": "ai_mail_composer",
            "html_field_composer": "ai_mail_composer",
            "chatter_ai_button": "ai_chatter_helper",
            "html_field_record": "ai_html_record",
            "html_field_text_select": "ai_mail_selector",
        }
        composer_key = caller_to_composer_map.get(caller, False)
        return self.env["ir.model.data"]._xmlid_to_res_id(f"ai.{composer_key}", raise_if_not_found=True)

    @api.model
    def create_ai_composer_channel(
        self,
        caller_component,
        record_name,
        record_model=None,
        record_id=None,
        front_end_info=None,
        text_selection=None,
    ):
        ai_composer_id = self._get_composer_from_caller(caller_component)
        if not ai_composer_id:
            raise AccessError(_("AI not reachable, composer ID not found"))
        # create a new AI chat
        channel = self.create(
            {
                "channel_member_ids": [
                    Command.create(
                        {
                            "partner_id": self.env.user.partner_id.id,
                        }
                    ),
                ],
                "channel_type": "ai_composer",
                "name": self.env._("AI: %(name)s", name=record_name),
                "ai_composer": ai_composer_id,
            }
        )
        original_record = self.env[record_model].browse(record_id)

        # Create the initial context for the model (add record info, chatter info, pre-prompts, etc.)
        channel.ai_context = original_record._ai_initialise_context(
            caller_component, channel.ai_composer.default_prompt, text_selection, front_end_info
        )

        return {"ai_channel_id": channel.id, "data": Store().add(channel).get_result()}

    @api.model
    def _get_or_create_ai_chat(self, partner):
        channel = self._find_ai_chat_channel(partner)
        if not channel:
            channel = self._create_ai_chat(partner)
        return channel

    def _find_ai_chat_channel(self, ai_partner):
        return self.search([
            ('is_member', '=', True),
            ('channel_type', '=', 'ai_chat'),
            ('channel_member_ids', 'any', [
                ('partner_id', '=', ai_partner.id)
            ])
        ])

    def _create_ai_chat(self, partner):
        guest = self.env["mail.guest"]._get_guest_from_context()
        with mute_logger("odoo.sql_db"):
            self.env.cr.execute(SQL(
                "SELECT pg_advisory_xact_lock(%s, %s) NOWAIT;",
                guest.id if self.env.user._is_public() else self.env.user.partner_id.id,
                partner.id
            ))

        channel = self.create({
            "channel_member_ids": [
                Command.create({"guest_id": guest.id} if self.env.user._is_public() else {"partner_id": self.env.user.partner_id.id}),
                Command.create({"partner_id": partner.id}),
            ],
            "channel_type": "ai_chat",
            # sudo() => visitor can set the name of the channel
            "name": partner.sudo().name,
        })
        return channel

    def _close_older_chat_channel(self, ai_partner):
        older_channel = self._find_ai_chat_channel(ai_partner)
        if older_channel:
            older_channel.sudo().unlink()

    def close_ai_chat(self):
        self.ensure_one()
        if self._should_unlink_on_close():
            self.sudo().unlink()

    def _should_unlink_on_close(self):
        return self.channel_type in ["ai_composer", "ai_chat"] and self.is_member

    def _ai_add_message_to_context(self, message, author):
        current_context = self.ai_context
        current_context.append(
            {
                "role": author,
                "content": message,
            }
        )
        self.ai_context = current_context

    def _ai_submit_to_model(self, prompt, conversation_history):
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        olg_api_endpoint = IrConfigParameter.get_param(
            "web_editor.olg_api_endpoint", DEFAULT_OLG_ENDPOINT
        )
        database_id = IrConfigParameter.get_param("database.uuid")
        try:
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat",
                params={
                    "prompt": prompt,
                    "conversation_history": conversation_history or [],
                    "database_id": database_id,
                },
                timeout=30,
            )
        except AccessError:
            return self.env._("⚠️ Oops, it looks like our AI is unreachable!")
        if response["status"] == "success":
            return response["content"]
        elif response["status"] == "error_prompt_too_long":
            return self.env._(
                "⚠️ Sorry, your prompt is too long. Try to say it in fewer words."
            )
        elif response["status"] == "limit_call_reached":
            return self.env._(
                "⚠️ You have reached the maximum number of requests for this service. Try again later."
            )
        else:
            return self.env._(
                "⚠️ Sorry, we could not generate a response. Please try again later."
            )

    def _ai_create_response(self, model_response):
        # add the model response in the context
        self._ai_add_message_to_context(model_response, "assistant")
        final_response = model_response
        # translate the markdown formatted text into HTML and sanitize the HTML
        if markdown:
            response_html = markdown(model_response, extras=['fenced-code-blocks', 'tables', 'strike'])
            final_response = html_sanitize(response_html)
        odoobot_id = self.env["ir.model.data"]._xmlid_to_res_id("base.partner_root")
        self.message_post(
            author_id=odoobot_id,
            body=final_response,
            message_type="comment",
            silent=True,
            subtype_xmlid="mail.mt_comment",
        )

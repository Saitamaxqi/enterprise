from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.im_livechat.models.discuss_channel import is_livechat_channel


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    # compute_sudo => livechat channels can be accessed by visitors
    livechat_with_ai_agent = fields.Boolean(compute="_compute_livechat_with_ai_agent", compute_sudo=True, store=True)

    @api.depends('livechat_bot_partner_ids', 'channel_member_ids.partner_id')
    def _compute_livechat_with_ai_agent(self):
        # livechat_bot_partner_ids, maintains a historical record of all partner_id values for bots that were members of this channel.
        # Even if A bot is removed from the channel, its partner_id is present in livechat_bot_partner_ids.
        current_bot_member_partner_ids = self.livechat_bot_partner_ids & self.channel_member_ids.partner_id
        ai_agent_partner_ids = self.env["ai.agent"].search([("partner_id", "in", current_bot_member_partner_ids.ids)]).partner_id
        for channel in self:
            channel_bot_partner_ids = channel.livechat_bot_partner_ids & channel.channel_member_ids.partner_id
            channel.livechat_with_ai_agent = bool(ai_agent_partner_ids & channel_bot_partner_ids)

    def _forward_scripted_chatbot(self, chatbot_script_id):
        # sudo - discuss.channel: let the AI Agent proceed to the forward step (change channel operator, add scripted chatbot
        # as member, remove AI Agent from channel and finally rename channel).
        channel_sudo = self.sudo()
        ai_agent_partner_id = channel_sudo.livechat_bot_partner_ids

        # add the scripted chatbot to the channel and post a "chatbot invited to the channel" notification
        channel_sudo._add_new_members_to_channel(
            create_member_params={'livechat_member_type': 'bot'},
            inviting_partner=ai_agent_partner_id,
            partners=chatbot_script_id.operator_partner_id,
        )

        channel_sudo._action_unfollow(partner=ai_agent_partner_id, post_leave_message=False)

        # finally, rename the channel to include the scripted chatbot's name
        channel_sudo._update_channel_info(
            livechat_failure="no_failure",
            livechat_operator_id=chatbot_script_id.operator_partner_id,
            operator_name=chatbot_script_id.title
        )
        posted_messages = chatbot_script_id.with_context(lang=chatbot_script_id._get_chatbot_language())._post_welcome_steps(self)
        self.channel_pin(pinned=True)
        Store(bus_channel=self).add(self, "livechat_with_ai_agent").bus_send()
        return posted_messages

    def _should_unlink_on_close(self):
        should_unlink = super()._should_unlink_on_close()
        return should_unlink or self.livechat_with_ai_agent and self.is_member

    def _get_allowed_channel_member_create_params(self):
        return super()._get_allowed_channel_member_create_params() + ["ai_agent_id"]

    def _store_livechat_operator_id_fields(self):
        return super()._store_livechat_operator_id_fields() + ["im_status"]

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [Store.Attr("livechat_with_ai_agent", predicate=is_livechat_channel)]

    def _sync_field_names(self):
        field_names = super()._sync_field_names()
        field_names[None].append(Store.Attr("livechat_with_ai_agent", predicate=is_livechat_channel))
        return field_names

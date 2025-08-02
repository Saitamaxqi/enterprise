# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug.exceptions import BadRequest

from odoo import _, http
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class AILivechatController(http.Controller):

    @http.route('/ai_livechat/forward_operator', methods=["POST"], type="jsonrpc", auth='public')
    @add_guest_to_context
    def forward_operator(self, channel_id):
        channel = request.env['discuss.channel'].search([('id', '=', channel_id)])
        if not channel or channel.channel_type != 'livechat' or not channel.is_member:
            raise BadRequest()
        url = request.httprequest.headers.get("Referer")
        # sudo() => visitor can retrieve the rule the matches the current URL
        livechat_channel_rule = request.env['im_livechat.channel.rule'].sudo().match_rule(
            channel_id=channel.livechat_channel_id.id,
            url=url
        )
        # Forward the chat to a scripted chatbot if defined on the livechat channel rule.
        # In such case, the scripted chatbot performs some steps first before forwarding to a human operator.
        # sudo() => The visitor should be able to forward the chat to a scripted chatbot or a human operator
        if livechat_channel_rule.chatbot_script_id:
            channel.sudo()._forward_scripted_chatbot(chatbot_script_id=livechat_channel_rule.chatbot_script_id)
            return {'success': True, 'store_data': Store().add(channel).get_result()}

        channel.sudo()._forward_human_operator()
        if channel.livechat_with_ai_agent:
            return {
                'success': False,
                'notification': _("There is no human agent available at the moment. Please try again later."),
                "notification_type": "warning"
            }
        return {
            'success': True,
            'notification': _("The conversation has been forwarded successfully."),
            "notification_type": "success"
        }

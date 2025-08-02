# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http, _
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


class AIWebsiteLivechatController(http.Controller):

    @http.route('/ai_website_livechat/create_chat_channel', methods=["POST"], type="jsonrpc", auth='public')
    @add_guest_to_context
    def create_chat_channel_with_ai_agent(self, ai_agent_partner_id):
        if not (ai_agent := request.env['ai.agent']._retrieve_agent_if_access_allowed(ai_agent_partner_id)):
            return

        store = Store()
        agent_partner = request.env['res.partner'].browse(ai_agent.partner_id.id)
        guest = request.env['mail.guest']
        if request.env.user._is_public():
            guest = guest.sudo()._get_or_create_guest(
                guest_name=self._get_guest_name(),
                country_code=request.geoip.country_code,
                timezone=request.env["mail.guest"]._get_timezone_from_request(request),
            )
            request.update_context(guest=guest)
        if guest:
            store.add_global_values(guest_token=guest.sudo()._format_auth_cookie())
        request.env['discuss.channel'].sudo()._close_older_chat_channel(agent_partner)
        channel = request.env['discuss.channel'].sudo()._create_ai_chat(agent_partner)
        request.env["res.users"]._init_store_data(store)
        store.add(channel)
        return {'channel_id': channel.id, 'store_data': store.get_result()}

    def _get_guest_name(self):
        return _("Visitor")

    @http.route('/ai_website_livechat/is_livechat_operator_available', methods=["POST"], type="jsonrpc", auth='public')
    @add_guest_to_context
    def is_livechat_operator_available(self, livechat_channel_id):
        country = request.env['res.country']
        if not request.env.user._is_public():
            country = request.env.user.country_id
        elif request.geoip.country_code:
            country = request.env["res.country"].search(
                [("code", "=", request.geoip.country_code)], limit=1
            )
        # sudo() => visitor can access the livechat channel to check if there is an operator available
        livechat_channel = request.env['im_livechat.channel'].sudo().search([('id', '=', livechat_channel_id)])
        if not livechat_channel:
            return False
        operator = livechat_channel._get_operator(country_id=country.id, lang=request.cookies.get("frontend_lang"))
        operator = operator - self.env.user
        return bool(operator)

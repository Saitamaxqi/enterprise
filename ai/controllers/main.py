from odoo import http
from odoo.http import request
from odoo.tools.mail import html_sanitize


class AIDraftComposerController(http.Controller):
    @http.route(["/ai/generate_w_composer"], type="jsonrpc", auth="user")
    def generate_text(self, prompt, channel_id):
        composer_channel = request.env['discuss.channel'].search([('id', '=', channel_id)], limit=1)
        # remove HTML tags from the prompt (LLMs get confused and format their replies using HTML)
        prompt = html_sanitize(prompt).striptags()
        # generate response by sending prompt to the chatgpt api
        response = composer_channel._ai_submit_to_model(prompt, composer_channel.ai_context)
        # add original prompt to the conversation history (context)
        composer_channel._ai_add_message_to_context(prompt, 'user')
        # post response as odoobot
        composer_channel._ai_create_response(response)

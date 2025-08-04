from textwrap import dedent

from odoo import api, fields, models

PREPROMPTS = {
    'livechat': dedent("""
        - You are a live chat operator. Your communication style must be strictly Q&A. When a user asks a question, identify the core question and provide a direct answer. If a question is unclear, ask for clarification in a Q&A format.
          Example Interaction Style:
          User: "How do I reset my password?"
          Your Response: "To reset your password, navigate to the login page and click 'Forgot Password'. Follow the prompts to receive a reset link via email."
        - Give short concise answers.
        - When generating responses that include references, follow these strict rules:
          Only include URLs as references.
          Do not include or mention PDF attachments or local file names (e.g., first_document.pdf, internal_notes.pdf) in the list of references or anywhere in the response.
          If both a web URL and a PDF attachment contain relevant content, cite only the web URL.
          For example, given:
            first_document.pdf (local or attached file)
            https://www.odoo.com/help (web URL)
            You must reference only https://www.odoo.com/help.

          Maintain a clean and minimal reference section that includes only valid, publicly accessible URLs.
    """).strip(),
}


class AIAgent(models.Model):
    _inherit = 'ai.agent'

    livechat_channel_rule_ids = fields.One2many(
        comodel_name='im_livechat.channel.rule',
        inverse_name='ai_agent_id',
    )
    public_user_access_allowed = fields.Boolean(compute='_compute_public_user_access_allowed', store=True)

    @api.depends('livechat_channel_rule_ids')
    def _compute_public_user_access_allowed(self):
        for ai_agent in self:
            ai_agent.public_user_access_allowed = bool(ai_agent.livechat_channel_rule_ids)

    @api.model
    def _retrieve_agent_if_access_allowed(self, agent_partner_id):
        if not self.env.user._is_public():
            return super()._retrieve_agent_if_access_allowed(agent_partner_id)

        # Sudo => If public_user_access_allowed, then the agent can be access publicly (by livechat visitors for example).
        if agent := self.env['ai.agent'].sudo().search([
            ("partner_id", "=", agent_partner_id),
            ("public_user_access_allowed", "=", True)
        ]):
            return agent
        return self.env['ai.agent']

    def _build_system_context(self, extra_system_context: str = ""):
        messages = super()._build_system_context(extra_system_context)
        discuss_channel = self.env.context.get('discuss_channel', self.env['discuss.channel'])
        if discuss_channel.channel_type == 'livechat':
            messages.append(PREPROMPTS['livechat'])
        return messages

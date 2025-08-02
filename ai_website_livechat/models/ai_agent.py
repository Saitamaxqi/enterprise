from odoo import api, fields, models


class AIAgent(models.Model):
    _inherit = 'ai.agent'

    used_on_website_snippet = fields.Boolean()

    @api.model
    def use_on_website_snippet(self, new_agent_id=None, old_agent_id=None):
        if old_agent := self.env['ai.agent'].search([('id', '=', old_agent_id)]):
            old_agent.used_on_website_snippet = False
        if new_agent := self.env['ai.agent'].search([('id', '=', new_agent_id)]):
            new_agent.used_on_website_snippet = True

    @api.depends('used_on_website_snippet')
    def _compute_public_user_access_allowed(self):
        super()._compute_public_user_access_allowed()
        website_snippet_agents = self.filtered('used_on_website_snippet')
        for website_snippet_agent in website_snippet_agents:
            website_snippet_agent.public_user_access_allowed = True

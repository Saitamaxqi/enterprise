from odoo import api, models


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    @api.model
    def _remove_ai_livechat_sessions(self):
        sessionsToBeDeleted = self.search(['|', ('livechat_with_ai_agent', '=', True), ('channel_type', '=', 'ai_chat')])
        sessionsToBeDeleted.unlink()

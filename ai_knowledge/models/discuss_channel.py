from odoo import models


class DiscussChannel(models.Model):
    """Chat Session
    Representing a conversation between users.
    It extends the base usage with AI assistant for knowledge functionality
    """

    _name = "discuss.channel"
    _inherit = ["discuss.channel"]

    def _get_composer_from_caller(self, caller):
        if caller == "html_field_knowledge":
            return self.env["ir.model.data"]._xmlid_to_res_id(
                "ai_knowledge.ai_html_knowledge"
            )
        return super()._get_composer_from_caller(caller)

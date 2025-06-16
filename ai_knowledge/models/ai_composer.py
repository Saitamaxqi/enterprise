from odoo import models, fields


class AIComposer(models.Model):
    """AI Composer Model Configurations
    It extends the base usage with AI assistant for knowledge functionality
    """

    _name = "ai.composer"
    _inherit = ["ai.composer"]

    interface_key = fields.Selection(
        selection_add=[("html_field_knowledge", "HTML Field 'AI' Shortcut for Knowledge")],
        ondelete={"html_field_knowledge": "cascade"},
    )

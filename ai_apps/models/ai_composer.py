# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AIComposer(models.Model):
    _name = "ai.composer"
    _description = "AI model configurations (system prompts) for text drafting."

    composer_name = fields.Char(
        "AI Composer Name", help="The identifier of the mail assistant"
    )
    display_name = fields.Char(related="composer_name")
    default_prompt = fields.Text(
        "Default Prompt", help="The default prompt passed to this mail assistant"
    )

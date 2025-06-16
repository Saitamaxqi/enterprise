from odoo import fields, models


class AIPromptButton(models.Model):
    _name = "ai.prompt.button"
    _description = "Prompt that can be attached to AI UI rules for quick access by the user."

    name = fields.Char(
        "AI Prompt", help="The prompt sent to the AI when clicked on"
    )
    sequence = fields.Integer(string="Sequence", default=10)
    composer_id = fields.Many2one("ai.composer", index='btree_not_null')

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from odoo.exceptions import UserError

INTERFACE_KEYS = [
    ("html_field_record", "HTML Field 'AI' Shortcut in Records"),
    ("html_field_composer", "HTML Field 'AI' Shortcut in Messages"),
    ("composer_ai_button", "Message / Note Composer Button"),
    ("html_field_text_select", "Text Selection Tooltip"),
    ("chatter_ai_button", "Chatter AI Button"),
    ("html_prompt_shortcut", "HTML Field 'Prompt' Shortcut in Mail Templates")
]


class AIComposer(models.Model):
    _name = "ai.composer"
    _description = "AI model configurations (system prompts) for text drafting."

    def _get_default_agent(self):
        return self.env["ir.model.data"]._xmlid_to_res_id("ai.ai_default_agent")

    name = fields.Char(
        "Rule Name", help="The identifier for the interface component to agent rule"
    )
    interface_key = fields.Selection(selection=INTERFACE_KEYS, string="Interface Key", required=True)
    focused_models = fields.Many2many('ir.model', string="Models")
    ai_agent = fields.Many2one('ai.agent', string="Agent", default=_get_default_agent)
    default_prompt = fields.Text(
        "Default Prompt", help="The default prompt passed to this mail assistant"
    )
    is_system_default = fields.Boolean('Is the rule a system default or user created', default=False, readonly=True, copy=False)
    available_prompts = fields.One2many('ai.prompt.button', 'composer_id', string="Available User Prompts")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_rules(self):
        if any(rule.is_system_default for rule in self):
            raise UserError(self.env._('System default prompts cannot be removed.'))

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for composer, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", composer.name)
        return vals_list

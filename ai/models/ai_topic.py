# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AITopic(models.Model):
    _name = 'ai.topic'
    _description = "Create a topic that leverages instructions and tools to direct Odoo AI in assisting the user with their tasks."

    name = fields.Char(string="Title")
    description = fields.Text(string="Description")
    instructions = fields.Text(string="Instructions")
    tool_ids = fields.Many2many('ai.tool', string="AI Tools")

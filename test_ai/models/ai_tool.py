# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.ai.utils.tools_schema.tools import register_ai_tool, AITerminate


class AITool(models.Model):
    _inherit = "ai.tool"

    @register_ai_tool({
        'description': 'sum two numbers',
        'parameters': {
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'number',
                    'description': 'The first operand'
                },
                'b': {
                    'type': 'number',
                    'description': 'The second operand'
                }
            },
            'required': ['a', 'b']
        }
    })
    def _sum_2_numbers(self, a, b):
        return a + b

    @register_ai_tool({
        'description': 'just terminate the conversation',
        'parameters': {
            'type': 'object',
            'properties': {
                'message': {
                    'type': 'string',
                    'description': 'The message to return to the user'
                }
            },
            'required': ['message']
        }
    })
    def _terminate_conversation(self, message):
        return AITerminate(message)


def _extend_ai_tool(schema):
    schema["description"] = "updated sum two numbers"
    schema["parameters"]["properties"]["b"]["description"] = "Optional second operand. Defaults to 0."
    schema["parameters"]["required"] = ["a"]
    return schema


class AITool2(models.Model):
    _inherit = "ai.tool"

    @register_ai_tool(_extend_ai_tool)
    def _sum_2_numbers(self, a, b=0):
        return super()._sum_2_numbers(a, b)

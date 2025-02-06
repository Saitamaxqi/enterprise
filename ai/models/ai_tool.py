# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import re

from odoo import api, fields, models


class AITool(models.Model):
    _name = 'ai.tool'
    _description = "A function that can be called by the AI"

    name = fields.Char()
    formatted_name = fields.Char(help=(
            "Lower case name in which spaces are replaced with underscores."
            "This is used as the name of the function to call which is used with the tools API of the LLM."
        ),
        compute="_compute_formatted_name", store=True, readonly=False)
    description = fields.Text(help="A brief description of the tool and its purpose.")
    input_schema = fields.Json(help=(
        """
            Defines the parameters required to use the tool, their type, a description for each parameter and whether the parameter is required.
            You can also define the format of the parameter which is a regex pattern that the parameter must match.
            For example the input schema of the feature that schedules a meeting with a salesperson:
            {
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "The name of person to schedule the meeting with"
                        "required": true,
                    },
                    "meeting_date": {
                        "type": "string",
                        "description": "The date on which the meeting will occur in format YYYY-mm-dd"
                        "required": true,
                        "format": "regex pattern to match the date format",
                    }
                }
            }
        """),
        required=True)
    server_action = fields.Many2one('ir.actions.server')
    result_prompt = fields.Text(string="Result Prompt")

    _unique_formatted_name = models.Constraint(
        'UNIQUE(formatted_name)',
        "The formatted name must be unique as it is required by the LLM to identify the tool",
    )

    @api.depends('name')
    def _compute_formatted_name(self):
        for tool in self:
            tool.formatted_name = tool.name.lower().replace(' ', '_')

    def _use_tool(self, arguments):
        """
        :param arguments: dictionary containing the arguments required to use the tool
        :return A string indicating whether the tool usage succeeded.
        :rtype: string
        """

        self.ensure_one()
        validation_result = self._validate_arguments(arguments)
        is_valid = validation_result.get('is_valid')
        if not is_valid:
            return validation_result.get('failure_reason')
        arguments['result_prompt'] = self.result_prompt
        return self.server_action.with_context(**arguments).run()

    def _validate_arguments(self, actual_arguments):
        expected_arguments = json.loads(self.input_schema)['properties']
        for expected_argument, expected_argument_description in expected_arguments.items():
            if expected_argument_description.get('required', True) and expected_argument not in actual_arguments:
                return {
                    'is_valid': False,
                    'failure_reason': f"Could you please provide info about {expected_argument} as it is required to process your request",
                }

            expected_format = expected_argument_description.get('format', False)
            if expected_format and not re.match(expected_format, actual_arguments.get(expected_argument)):
                return {
                    'is_valid': False,
                    'failure_reason': (
                        f"The value of the parameter {expected_argument} doesn't "
                        f"match the expected format {expected_argument_description.get('format')}"
                    ),
                }
        return {'is_valid': True}

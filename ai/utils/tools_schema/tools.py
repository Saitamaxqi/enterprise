# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import api
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.addons.ai.utils.tools_schema.validators import validate_params_llm_values_with_schema

_logger = logging.getLogger(__name__)


def register_ai_tool(schema):
    """Decorator to register a method as an AI tool with the provided schema.

    - The method will be automatically wrapped with api.model.
    - IMPORTANT: To completely register a method as an AI tool, create an `ai.tool` record normally via data file in xml.

    :param schema: Either a dictionary containing the schema definition or a callable function
                  that takes a dictionary and returns an augmented schema. The original declaration
                  of the method should be decorated with a dict schema, while overrides can only
                  be decorated with a function schema for extensibility.
    """
    if not schema:
        raise ValueError("Schema is required for AI tool registration.")

    def decorator(func):
        wrapped = api.model(func)
        wrapped._ai_tool_schema = schema
        return wrapped

    return decorator


def call_ai_tool(AITool, tool_call):
    function = tool_call['function']
    tool_call_id = tool_call['id']
    method_name = function['name']

    ai_tool = AITool.search(Domain('method_name', '=', method_name))
    if not ai_tool:
        raise ValidationError(AITool.env._("Error: Tool %s not found.", method_name))

    schema = ai_tool.schema
    func_args_json = json.loads(function['arguments'])
    input_schema = schema["function"]["parameters"]["properties"]
    required_parameters = schema["function"]["parameters"]["required"]
    validate_params_llm_values_with_schema(func_args_json, input_schema, required_parameters)

    _logger.info("AI Tool %s called with arguments: %s", method_name, func_args_json)

    schema_map, method_map = AITool._get_schema_and_method_maps()
    if method_name not in schema_map:
        raise ValidationError(AITool.env._("Error: Method %s is not registered as an AI tool.", method_name))

    method = method_map.get(method_name)
    if not method:
        raise ValidationError(AITool.env._("Error: Method %s is not callable.", method_name))

    result = method(AITool, **func_args_json)
    return {
        "content": result is None and 'success' or result,
        "role": "tool",
        "tool_call_id": tool_call_id,
    }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy

from odoo import fields, models, api
from odoo.tools import frozendict, ormcache
from odoo.addons.ai.utils.tools_schema.validators import validate_schema


def freeze_recursive(obj):
    """Return a frozen version of the object, recursively.

    - Dicts become frozendict
    - Lists become tuples
    - Sets become frozensets
    - Other objects are returned as-is
    """
    if isinstance(obj, dict):
        return frozendict({k: freeze_recursive(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(freeze_recursive(item) for item in obj)
    elif isinstance(obj, set):
        return frozenset(freeze_recursive(item) for item in obj)
    else:
        return obj


class AITool(models.Model):
    _name = 'ai.tool'
    _description = "Representation of exposed AI tools"

    name = fields.Char(string="Name")
    method_name = fields.Char(string="Method Name")
    schema = fields.Json(string="Schema", compute="_compute_schema")
    description = fields.Text(string="Description", compute="_compute_schema")

    @api.model
    @ormcache()
    def _get_schema_and_method_maps(self):
        schema_map, method_map = {}, {}
        for model_cls in reversed(self._model_classes__):
            for name, value in model_cls.__dict__.items():
                is_ai_tool = callable(value) and hasattr(value, "_ai_tool_schema")
                if is_ai_tool:
                    method_map[name] = value
                    schema = value._ai_tool_schema
                    if name not in schema_map:
                        # first encounter of method: it's a base schema, should be a dict
                        if not (schema and isinstance(schema, dict)):
                            raise ValueError("Base schema must be a non-empty dictionary.")
                        schema_map[name] = copy.deepcopy(schema)
                    else:
                        # schema override, should be a callable
                        if not callable(schema):
                            raise TypeError("Schema extension must be a callable function.")
                        schema_map[name] = schema(schema_map[name])

        return (
            freeze_recursive(
                {
                    name: {
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": schema["description"],
                            "parameters": schema["parameters"],
                        },
                    }
                    for name, schema in schema_map.items()
                }
            ),
            frozendict(method_map),
        )

    def _register_hook(self):
        """Validate the registered ai.tool's compiled schemas."""
        schema_map = self._get_schema_and_method_maps()[0]
        for ai_tool in self.search([("method_name", "in", list(schema_map.keys()))]):
            validate_schema(ai_tool.schema["function"])
        return super()._register_hook()

    @api.depends("method_name")
    def _compute_schema(self):
        schema_map = self._get_schema_and_method_maps()[0]
        for ai_tool in self:
            if ai_tool.method_name not in schema_map:
                ai_tool.schema = None
                ai_tool.description = ""
                continue
            ai_tool.schema = schema_map[ai_tool.method_name]
            ai_tool.description = ai_tool.schema["function"]["description"]

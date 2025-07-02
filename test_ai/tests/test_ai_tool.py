# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from odoo.tests import tagged, Like
from odoo.exceptions import ValidationError
from odoo.addons.base.tests.common import TransactionCase
from odoo.addons.ai.utils.tools_schema.tools import call_ai_tool


@tagged("post_install", "-at_install")
class TestAITool(TransactionCase):
    def _call_tool(self, id, method, kwargs):
        tool_call = {
            "id": id,
            "function": {
                "name": method,
                "arguments": json.dumps(kwargs),
            }
        }
        return call_ai_tool(self.env["ai.tool"], tool_call)

    def test_call_tool(self):
        with self.assertLogs("odoo.addons.ai.utils.tools_schema.tools", logging.INFO) as capture:
            result = self._call_tool(1, "_sum_2_numbers", {"a": 1, "b": 2})
            self.assertEqual(result["content"], 3)
        self.assertEqual(capture.output, [Like("...AI Tool _sum_2_numbers called with arguments: {'a': 1, 'b': 2}")])

    def test_call_tool_with_invalid_arguments(self):
        with self.assertRaises(ValidationError) as context:
            self._call_tool(1, "_sum_2_numbers", {"a": 1, "b": "three"})
        self.assertIn("The type of the parameter 'b' is incorrect. It should be 'number'.", str(context.exception))

    def test_call_non_existent_tool(self):
        with self.assertRaises(ValidationError) as context:
            self._call_tool(1, "non_existent_tool", {})
        self.assertIn("Tool non_existent_tool not found.", str(context.exception))

    def test_tool_schema_override(self):
        ai_tool = self.env["ai.tool"].search([("method_name", "=", "_sum_2_numbers")], limit=1)
        schema = ai_tool.schema
        description = ai_tool.description
        self.assertEqual(schema["function"]["parameters"]["required"], ["a"])
        self.assertEqual(description, "updated sum two numbers")

        with self.assertLogs("odoo.addons.ai.utils.tools_schema.tools", logging.INFO) as capture:
            result = self._call_tool(1, "_sum_2_numbers", {"a": 1})
            self.assertEqual(result["content"], 1)

        self.assertEqual(capture.output, [Like("...AI Tool _sum_2_numbers called with arguments: {'a': 1}")])

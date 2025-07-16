# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged, Like
from odoo.exceptions import ValidationError
from odoo.addons.base.tests.common import TransactionCase
from odoo.addons.ai.utils.tools_schema.tools import call_ai_tool


@tagged("post_install", "-at_install")
class TestAITool(TransactionCase):
    def _create_agent_with_tools(self, name="Test Agent", tool_refs=None):
        partner = self.env["res.partner"].create({"name": f"Partner for {name}"})
        agent_vals = {
            "name": name,
            "partner_id": partner.id,
        }
        if tool_refs:
            agent_vals["topic_ids"] = [
                Command.create({
                    "name": f"Topic for {name}",
                    "tool_ids": [
                        Command.set([self.env.ref(ref).id for ref in tool_refs]),
                    ],
                }),
            ]
        return self.env["ai.agent"].create(agent_vals)

    def _call_tool(self, id, method, kwargs):
        tool_call = {
            "id": id,
            "function": {
                "name": method,
                "arguments": json.dumps(kwargs),
            }
        }
        tool_call_result = call_ai_tool(self.env["ai.tool"], tool_call)
        return tool_call_result[2]

    def _create_mock_response(self, response_content, tools_name_arguments):
        if not tools_name_arguments:
            tools_name_arguments = []
        tool_calls = []
        for tool_no, tool in enumerate(tools_name_arguments):
            tool_calls.append({
                "id": f"call_{tool_no + 1}",
                "function": {
                    "name": tool["name"],
                    "arguments": json.dumps(tool["arguments"])
                }
            })
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response_content if response_content else None,
                    "tool_calls": tool_calls if tool_calls else None
                }
            }]
        }

    def test_call_tool(self):
        with self.assertLogs("odoo.addons.ai.utils.tools_schema.tools", logging.INFO) as capture:
            result = self._call_tool(1, "_sum_2_numbers", {"a": 1, "b": 2})
            self.assertEqual(result, 3)
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
            self.assertEqual(result, 1)

        self.assertEqual(capture.output, [Like("...AI Tool _sum_2_numbers called with arguments: {'a': 1}")])

    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService.get_completion")
    def test_generate_response_with_ai_terminate(self, mock_get_completion):
        agent = self._create_agent_with_tools(
            name="Test Agent with Terminate",
            tool_refs=["test_ai.tool_terminate_conversation"]
        )
        mock_get_completion.return_value = self._create_mock_response(
            response_content=None,
            tools_name_arguments=[{
                "name": "_terminate_conversation",
                "arguments": {"message": "Task completed successfully!"}
            }]
        )
        response = agent._generate_response("Please terminate the conversation")
        self.assertEqual(response, ["Task completed successfully!"])
        self.assertEqual(mock_get_completion.call_count, 1)

    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService.get_completion")
    def test_content_ignored_when_all_tools_terminate(self, mock_get_completion):
        agent = self._create_agent_with_tools(
            name="Test Agent Content Ignored",
            tool_refs=["test_ai.tool_terminate_conversation"]
        )
        mock_get_completion.return_value = self._create_mock_response(
            response_content="This content should be ignored",
            tools_name_arguments=[
                {
                    "name": "_terminate_conversation",
                    "arguments": {"message": "First termination"}
                },
                {
                    "name": "_terminate_conversation",
                    "arguments": {"message": "Second termination"}
                }
            ]
        )
        response = agent._generate_response("Test prompt")
        self.assertEqual(set(response), {"First termination", "Second termination"})
        self.assertNotIn("This content should be ignored", response)

    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService.get_completion")
    def test_content_ignored_when_all_tools_terminate_2(self, mock_get_completion):
        # Even if all tools terminate without providing a termination message, the content should be ignored.
        agent = self._create_agent_with_tools(
            name="Test Agent Content Ignored",
            tool_refs=["test_ai.tool_terminate_conversation"]
        )
        mock_get_completion.return_value = self._create_mock_response(
            response_content="This content should be ignored",
            tools_name_arguments=[
                {
                    "name": "_terminate_conversation",
                    "arguments": {"message": ""}
                },
                {
                    "name": "_terminate_conversation",
                    "arguments": {"message": ""}
                }
            ]
        )
        response = agent._generate_response("Test prompt")
        self.assertEqual(response, [])
        self.assertNotIn("This content should be ignored", response)

    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService.get_completion")
    def test_mixed_tool_calls_continue_generation(self, mock_get_completion):
        agent = self._create_agent_with_tools(
            name="Test Agent Mixed Tools",
            tool_refs=["test_ai.tool_sum_2_numbers", "test_ai.tool_terminate_conversation"]
        )
        first_response = self._create_mock_response(
            response_content=None,
            tools_name_arguments=[
                {
                    "name": "_sum_2_numbers",
                    "arguments": {"a": 5, "b": 3}
                },
                {
                    "name": "_terminate_conversation",
                    "arguments": {"message": "Partial termination"}
                }
            ]
        )
        second_response = self._create_mock_response(
            response_content="The sum is 8. Task completed!",
            tools_name_arguments=None
        )
        mock_get_completion.side_effect = [first_response, second_response]
        response = agent._generate_response("Calculate 5+3 and then terminate")
        self.assertEqual(response, ["The sum is 8. Task completed!"])
        self.assertEqual(mock_get_completion.call_count, 2)

    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService.get_completion")
    def test_mixed_tool_calls_with_content_continue_generation(self, mock_get_completion):
        agent = self._create_agent_with_tools(
            name="Test Agent Mixed Tools With Content",
            tool_refs=["test_ai.tool_sum_2_numbers", "test_ai.tool_terminate_conversation"]
        )
        first_response = self._create_mock_response(
            response_content="Content with non-terminating tool calls",
            tools_name_arguments=[{
                "name": "_sum_2_numbers",
                "arguments": {"a": 5, "b": 3}
            }, {
                "name": "_terminate_conversation",
                "arguments": {"message": "Partial termination"}
            }]
        )
        second_response = self._create_mock_response(
            response_content="The sum is 8. Task completed!",
            tools_name_arguments=None
        )
        mock_get_completion.side_effect = [first_response, second_response]
        response = agent._generate_response("Calculate 5+3 and then terminate")
        self.assertEqual(response, ["Content with non-terminating tool calls", "The sum is 8. Task completed!"])
        self.assertEqual(mock_get_completion.call_count, 2)

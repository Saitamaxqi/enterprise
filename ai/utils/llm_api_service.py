# Part of Odoo. See LICENSE file for full copyright and licensing details.
import copy
import json
import os
import requests
import typing
from logging import getLogger
import time
from typing import Callable, Any

from odoo import _
from odoo.api import Environment
from odoo.exceptions import UserError

_logger = getLogger(__name__)


class ChatMessage(typing.TypedDict):
    role: str
    content: str


class Embedding(typing.TypedDict):
    index: int
    embedding: list[float]
    object: str


class EmbeddingResponse(typing.TypedDict):
    object: str
    data: list[Embedding]
    model: str
    usage: dict


class LLMApiService:
    def __init__(self, env: Environment, provider: str = 'openai') -> None:
        self.provider = provider
        base_url = None
        if self.provider == 'openai':
            base_url = "https://api.openai.com/v1"
        elif self.provider == 'google':
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

        self.base_url = base_url
        self.env = env

    def get_completion(
        self,
        messages: list[ChatMessage],
        model: str = 'gpt-4',
        store: bool | None = None,
        reasoning_effort: str | None = None,
        metadata: dict | None = None,
        frequency_penalty: float | None = None,
        logit_bias: dict | None = None,
        logprobs: bool | None = None,
        top_logprobs: int | None = None,
        max_completion_tokens: int | None = None,
        n: int | None = None,
        modalities: list[str] | None = None,
        prediction: dict | None = None,
        audio: dict | None = None,
        presence_penalty: float | None = None,
        response_format: dict | None = None,
        seed: int | None = None,
        service_tier: str | None = None,
        stop: str | list[str] | None = None,
        stream: bool | None = None,
        stream_options: dict | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        parallel_tool_calls: bool | None = None,
        user: str | None = None,
    ):
        body = {
            'model': model,
            'messages': messages
        }

        self._add_if_set(body, 'store', store)
        self._add_if_set(body, 'reasoning_effort', reasoning_effort)
        self._add_if_set(body, 'metadata', metadata)
        self._add_if_set(body, 'frequency_penalty', frequency_penalty)
        self._add_if_set(body, 'logit_bias', logit_bias)
        self._add_if_set(body, 'logprobs', logprobs)
        if logprobs:
            self._add_if_set(body, 'top_logprobs', top_logprobs)
        self._add_if_set(body, 'max_completion_tokens', max_completion_tokens)
        self._add_if_set(body, 'n', n)
        self._add_if_set(body, 'modalities', modalities)
        self._add_if_set(body, 'prediction', prediction)
        if modalities and 'audio' in modalities:
            self._add_if_set(body, 'audio', audio)
        self._add_if_set(body, 'presence_penalty', presence_penalty)
        self._add_if_set(body, 'response_format', response_format)
        self._add_if_set(body, 'seed', seed)
        self._add_if_set(body, 'service_tier', service_tier)
        self._add_if_set(body, 'stop', stop)
        self._add_if_set(body, 'stream', stream)
        if stream:
            self._add_if_set(body, 'stream_options', stream_options)
        self._add_if_set(body, 'temperature', temperature)
        self._add_if_set(body, 'top_p', top_p)
        self._add_if_set(body, 'tools', tools)
        self._add_if_set(body, 'tool_choice', tool_choice)
        self._add_if_set(body, 'parallel_tool_calls', parallel_tool_calls)
        self._add_if_set(body, 'user', user)

        return self._request(
            'post',
            '/chat/completions',
            self._get_base_headers(),
            body,
        )

    def get_embedding(
        self,
        input: str | list[str] | list[int] | list[list[int]],
        dimensions: int,
        model: str = 'text-embedding-3-small',
        encoding_format: str | None = None,
        user: str | None = None,
    ) -> EmbeddingResponse:
        body = {
            'input': input,
            'model': model
        }
        self._add_if_set(body, 'encoding_format', encoding_format)
        self._add_if_set(body, 'dimensions', dimensions)
        self._add_if_set(body, 'user', user)

        return self._request(
            'post',
            '/embeddings',
            self._get_base_headers(),
            body,
        )

    def get_transcription(
            self,
            data: bytes,
            mimetype: str = "audio/ogg",
            model: str = "whisper-1",
            prompt: str | None = None,
            response_format: str = "verbose_json",
            temperature: float | None = None
    ):
        """ Submit audio data for transcription and return the transcribed text
            Logs real-time factor:  `o_rtf = (transmission + inference_time) / audio_duration`
            :param data: The audio file as raw bytes (not a filename or path!).
            :param mimetype: MIME type of the audio data, defaults to "audio/ogg".
            :param model: model to use for the transcription, defaults to 'whisper-1'
            :param prompt: Optional text used to guide the model's style or continue a previous audio segment. Only supports english.
            :param response_format: format of the output of the model. Types: 'json', 'text', 'srt', 'verbose_json', or 'vtt'
            :param temperature: randomness level of the model. Ranges from 0 to 1.
            :return: str | None: The transcribed text if successful, or None if the transcription failed.

            Example:
            ```python
            from odoo.addons.ai.utils.llm_api_service import LLMApiService
            service = LLMApiService(self.env)
            with open("audio.ogg", "rb") as f:
                audio_bytes = f.read()
            text = service.get_transcription(audio_bytes, mimetype="audio/ogg")
            ```
        """
        if response_format not in ['json', 'verbose_json']:  # limitation of using response.json() in _request function
            raise NotImplementedError(f"Response format '{response_format}' is not supported. Request must return json!")

        headers = {
            'Authorization': f'Bearer {self._get_api_token()}',
        }
        body = {
            "model": model,
            "response_format": response_format
        }
        self._add_if_set(body, "prompt", prompt)
        self._add_if_set(body, "temperature", temperature)

        start = time.time()
        response = self._request(
            method="post",
            endpoint="/v1/audio/transcriptions",
            headers=headers,
            body={},
            data=body,
            files={"file": ("audio", data, mimetype)},
        )
        elapsed = time.time() - start

        if not response or 'text' not in response:
            _logger.warning("No transcription received.")
            return None

        # Observed RTF (request time + transcription time)
        o_rft_text = ""
        audio_duration = response.get('duration', False)
        if audio_duration and audio_duration > 0:
            o_rtf = elapsed / audio_duration
            o_rft_text = f"(Observed RTF: {o_rtf:.2f} for {audio_duration:.1f}s audio)"
        _logger.info("Transcription job done in %.1fs %s", elapsed, o_rft_text)
        return response.get('text')

    def _add_if_set(self, d: dict, key: str, value):
        if value is not None:
            d[key] = value

    def _get_base_headers(self) -> dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._get_api_token()}',
        }

    def _get_api_token(self):
        config_param_sudo = self.env['ir.config_parameter'].sudo()
        if self.provider == 'openai' and config_param_sudo.get_param('ai.openai_key'):
            return config_param_sudo.get_param('ai.openai_key')
        elif self.provider == 'google' and config_param_sudo.get_param('ai.google_key'):
            return config_param_sudo.get_param('ai.google_key')
        elif api_key := os.getenv('ODOO_AI_CHATGPT_TOKEN'):
            return api_key
        raise UserError(_("No API key set for provider '%s'", self.provider))

    def _request(self, method: str, endpoint: str, headers: dict[str, str], body: dict, data: dict | None = None, files: dict | None = None) -> dict:
        route = f"{self.base_url}/{endpoint.strip('/')}"
        try:
            response = requests.request(
                method,
                route,
                headers=headers,
                json=body,
                data=data,
                timeout=30,
                files=files
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            message = f"LLM API request failed: {e!r}"
            if e.response is not None:
                try:
                    message += f" {json.dumps(e.response.json(), indent=2)}"
                except ValueError:  # catch JSON decode errors
                    message += f" {e.response.text}"
            _logger.warning(message)
            raise

    def _request_llm(
        self, llm_model, system_prompts, user_prompts, tools=None,
        files=None, schema=None, temperature=0.2, inputs=(),
    ):
        """Make a single request to the LLM.

        > https://platform.openai.com/docs/guides/responses-vs-chat-completions#why-the-responses-api
        > https://platform.openai.com/docs/guides/pdf-files?api-mode=responses
        > https://platform.openai.com/docs/guides/function-calling?api-mode=responses

        Return:
        - a list of responses
        - a list of tuple of the tools to call
            [(tool_name, call_id, {argument_1: True, argument_2: 3})]
        - a list of inputs to include in the next call in addition to the tool response
        """
        user_content = [{"type": "input_text", "text": prompt} for prompt in user_prompts]

        if files:
            user_content.extend(
                {'type': 'input_text', 'text': file['value']}
                if file['type'] == 'text' else
                {'type': 'input_image', 'image_url': file['value']}
                if file['type'] == 'image' else
                {'type': 'input_file', 'filename': f"file_{idx}.pdf", 'file_data': file['value']}
                for idx, file in enumerate(files, start=1)
            )

        body = {
            "model": llm_model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {"type": "input_text", "text": prompt}
                        for prompt in system_prompts
                    ],
                },
                {"role": "user", "content": user_content},
                *inputs,
            ],
            "store": False,
            "temperature": temperature,
        }
        if schema:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "json_schema",
                    "schema": schema,
                    "strict": True,
                },
            }

        if tools:
            body["tools"] = self._to_open_ai_tool_schema([{
                "description": tool_description,
                "parameters": tool_parameter_schema,
                "type": "function",
                "name": tool_name,
                "strict": True,
            } for tool_name, (tool_description, _tool_call, tool_parameter_schema) in tools.items()])

        llm_response = self._request(
            "post",
            "/responses",
            self._get_base_headers(),
            body,
        )

        to_call = []
        response = []
        next_inputs = list(inputs or ())

        for line in llm_response.get("output") or ():
            if line.get('type') == 'function_call':
                tool_name = line.get("name", "")
                if tool_name not in tools:
                    _logger.error("AI: Try to call a forbidden action %s", line)
                    continue

                try:
                    arguments = json.loads(line.get("arguments") or "")
                except json.decoder.JSONDecodeError:
                    _logger.error("AI: Malformed arguments: %s", line)
                    continue

                to_call.append((tool_name, line.get('call_id'), arguments))
                next_inputs.append(line)

            elif text := line.get('text'):
                response.append(text)
            elif line.get('type') == 'message':
                response.extend(t for c in line.get('content', ()) if (t := c.get('text')))
        return response, to_call, next_inputs

    def request_llm(
        self, llm_model: str, system_prompts: list[str], user_prompts: list[str],
        tools: dict[str, tuple[str, Callable[[dict[str, Any]], Any], dict]] | None = None,
        files: list[dict] | None = None, schema: dict | None = None, temperature: float = 0.2,
    ) -> list[str]:
        """Same as `_request_llm`, but will call the tools until we are done.

        >>> files = [
        >>>     {'type': 'text', 'value': 'text content', 'file_ref': '<file_#1>'},
        >>>     {'type': 'image', 'value': 'data:image/png;base64,aW1hZ2UgY29udGVudA==', 'file_ref': '<file_#2>'},
        >>>     {'type': 'pdf', 'value': 'data:application/pdf;base64,cGRmIGNvbnRlbnQ=', 'file_ref': '<file_#3>'},
        >>> ]

        >>> tools = {
        >>>     "function_1": (
        >>>         "This function compute a sum",
        >>>         lambda arguments: arguments['a'] + arguments['b'],
        >>>         json_schema,
        >>>     ),
        >>>     "function_2": ...
        >>> }
        > https://json-schema.org/
        """
        assert self.provider == "openai", "Not implemented"

        AI_MAX_SUCCESSIVE_CALLS = int(self.env["ir.config_parameter"].sudo()
            .get_param("ai.max_successive_calls", "5"))

        AI_MAX_TOOL_CALLS_PER_CALL = int(self.env["ir.config_parameter"].sudo()
            .get_param("ai.max_tool_calls_per_call", "5"))

        if tools:
            tools = copy.deepcopy(tools)
            for _tool_description, _tool_call, tool_parameter_schema in tools.values():
                tool_parameter_schema["properties"]["__end_message"] = {
                    "type": "string",
                    "description": "If you are not waiting a result, and you are done, write here what you did and why. If you will do action after this one, leave it empty.",
                }
                if "__end_message" not in tool_parameter_schema["required"]:
                    tool_parameter_schema["required"].append("__end_message")

        inputs = []
        all_responses = []
        for api_call in range(AI_MAX_SUCCESSIVE_CALLS):
            responses, next_actions, inputs = self._request_llm(
                llm_model,
                system_prompts,
                user_prompts,
                files=files,
                inputs=inputs,
                schema=schema,
                tools=tools,
                temperature=temperature,
            )
            all_responses.extend(responses)

            if not next_actions:
                break

            done = False
            for tool_name, call_id, arguments in next_actions[:AI_MAX_TOOL_CALLS_PER_CALL]:
                if tool_name not in tools:
                    _logger.error("AI: Try to call a forbidden action %s", tool_name)
                    continue

                end_message = arguments.pop("__end_message", None)
                result, error = tools[tool_name][1](arguments=arguments)

                inputs.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": str(result),
                })

                if end_message and error is None:
                    all_responses.append(end_message)
                    done = True
                    _logger.info("AI: action terminate early: %s", end_message)

            if done:
                break

        _logger.info("AI: API calls %s", api_call + 1)

        return all_responses

    def _to_open_ai_tool_schema(self, schema):
        """Convert the tool schema if needed.

        Open AI `responses` endpoints needs all parameters to be in the
        "required" list, but it accepts `"type": ["string", "null"]`.

        So we convert the base JSON schema to the array version if needed.
        """
        if self.provider != "openai":
            return schema

        for tool in schema:
            required = tool["parameters"]["required"]
            non_required = set(tool["parameters"]["properties"]) - set(required)
            for name in non_required:
                tool["parameters"]["properties"][name]["type"] = [tool["parameters"]["properties"][name]["type"], "null"]
            tool["parameters"]["required"].extend(non_required)
            tool["parameters"]["additionalProperties"] = False
        return schema

# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os
import requests
import typing
from logging import getLogger
import time

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
            base_url = "https://api.openai.com"
        elif self.provider == 'google':
            base_url = "https://generativelanguage.googleapis.com"

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
            '/v1/chat/completions',
            self._get_base_headers(),
            body,
        )

    def get_embedding(
        self,
        input: str | list[str] | list[int] | list[list[int]],
        model: str = 'text-embedding-3-small',
        encoding_format: str | None = None,
        dimensions: int | None = None,
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
            '/v1/embeddings',
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
                timeout=20,
                files=files
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.warning("LLM API request to %s failed: %s", route, e)
            raise UserError(_("LLM API request failed: %s", e))

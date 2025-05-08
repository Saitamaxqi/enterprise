# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import lxml.html

from odoo import api, fields, models, _
from odoo.addons.ai.models.discuss_channel import DEFAULT_OLG_ENDPOINT
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError
from odoo.tools import is_html_empty
from odoo.tools.mail import html_sanitize

_logger = logging.getLogger(__name__)


class AIComposer(models.Model):
    _name = "ai.composer"
    _description = "AI model configurations (system prompts) for text drafting."

    name = fields.Char(
        "AI Composer Name", help="The identifier of the mail assistant"
    )
    default_prompt = fields.Text(
        "Default Prompt", help="The default prompt passed to this mail assistant"
    )

    def _generate_response(self, prompt, additional_ai_context=None):
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        olg_api_endpoint = IrConfigParameter.get_param("web_editor.olg_api_endpoint", DEFAULT_OLG_ENDPOINT)
        database_id = IrConfigParameter.get_param("database.uuid")

        system_prompt = self.default_prompt.strip()
        if additional_ai_context:
            system_prompt += "\n\nUse the following information when necessary to generate the response:\n\n"
            system_prompt += "\n".join(f"{key}: {value}" for key, value in additional_ai_context.items())

        _logger.debug("Generating response for prompt: %s", prompt)
        response = iap_tools.iap_jsonrpc(
            olg_api_endpoint + "/api/olg/1/chat",
            params={
                "prompt": prompt,
                "conversation_history": [{"role": "system", "content": system_prompt}],
                "database_id": database_id,
            },
            timeout=30,
        )
        if response["status"] == "success":
            return response["content"]

        raise UserError(_("Unable to generate response"))

    @api.model
    def _eval_ai_prompts(self, ai_composer, html, additional_ai_context=None):
        """Evaluate AI prompts in the given HTML content. If no composer, remove all the prompts."""
        if is_html_empty(html):
            return html

        Wrapper = html.__class__
        root = lxml.html.fromstring(html)

        prompt_containers = root.xpath("//div[hasclass('o_editor_prompt')]")

        if not prompt_containers:
            return Wrapper(html)

        for container in prompt_containers:
            prompt_content_elements = container.xpath(
                ".//div[hasclass('o_editor_prompt_content')]"
            )

            if not ai_composer:
                container.getparent().remove(container)
                continue

            if not prompt_content_elements:
                container.getparent().remove(container)
                continue

            assert (
                len(prompt_content_elements) == 1
            ), "There should be only one prompt content element inside a prompt container."
            prompt_text = prompt_content_elements[0].text_content().strip()

            if not prompt_text:
                container.getparent().remove(container)
                continue

            response = ai_composer._generate_response(prompt_text, additional_ai_context)

            if not response:
                container.getparent().remove(container)
                continue

            # Wrapped each line of the response in a <p> tag.
            wrapped_content = "\n".join(f"<p>{content}</p>" for content in response.split("\n") if content.strip())
            replacement_html_str = html_sanitize(wrapped_content, sanitize_attributes=True, sanitize_style=True)
            container.getparent().replace(container, lxml.html.fromstring(replacement_html_str))

        return Wrapper(lxml.html.tostring(root, encoding="unicode", method="html"))

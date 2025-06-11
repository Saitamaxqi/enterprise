import json
import logging

import werkzeug.exceptions
import requests

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

from ..utils.html_text_processor import HTMLTextProcessor

_logger = logging.getLogger(__name__)


class AIWebsiteController(http.Controller):

    @http.route(['/ai_website/generate_page'], type='jsonrpc', auth='user', website=True)
    def generate_website_page_content(self, instructions, name, sectionsArch, tone, **post):
        """Generate website content using the AI agent with text-only processing."""
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()

        try:
            agent = request.env.ref('ai_website.website_page_generator_agent')
        except ValueError:
            _logger.error("Website page generator agent not found. Please ensure the ai_website module data is properly installed.")
            return {'html': sectionsArch}

        text_processor = HTMLTextProcessor()
        batches = text_processor.extract_text_nodes(sectionsArch)
        current_website = request.website
        website_name = current_website.name
        website_default_lang_id = current_website.default_lang_id
        if not batches:
            return {'html': sectionsArch}

        context = f"""- Page name: {name} - Instructions: {instructions} - Tone: {tone} - lang: {website_default_lang_id.code} - website_name: {website_name}"""
        all_responses = {}
        try:
            # Process each batch of text nodes
            for batch in batches:
                prompt = json.dumps(batch, ensure_ascii=False)
                response = agent.get_direct_response(prompt, context)
                if response:
                    try:
                        batch_response = json.loads(response[0])
                        if batch_response:
                            all_responses.update(batch_response)
                    except json.JSONDecodeError:
                        continue
        except (UserError, requests.exceptions.RequestException) as e:
            _logger.error("Error generating website page content: %s", e)
            return {'html': sectionsArch, 'error': str(e)}

        if not all_responses:
            return {'html': sectionsArch}

        updated_sectionsArch = text_processor.process_ai_response(all_responses, sectionsArch)
        return {'html': updated_sectionsArch}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
import logging
from collections import defaultdict
from datetime import timedelta
from markupsafe import Markup
from textwrap import dedent
try:
    from markdown2 import markdown
except ImportError:
    markdown = None

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import file_open, html_sanitize, SQL
from odoo.tools.mail import html_to_inner_content

from ..utils.llm_api_service import LLMApiService
from ..utils.url_scraping import URLScraper

_logger = logging.getLogger(__name__)

# Pre-prompts and constants
SELECTION_MODELS = {
    'openai': [('gpt-3.5-turbo', "GPT-3.5 Turbo"), ('gpt-4', "GPT-4")],
    'google': [('gemini', "Gemini")],
}

PROVIDERS_MODELS = {
    provider: {model[0] for model in SELECTION_MODELS[provider]}
    for provider in SELECTION_MODELS
}

TEMPERATURE_MAP = {
    'analytical': 0.2,
    'balanced': 0.5,
    'creative': 0.8,
}

# Pre-prompts are put in a dictionary so that they can easily be overridden
PREPROMPTS = {
    'default_system_prompt': "You are a RAG assistant.",
    'tools': dedent("""
        You have access to tools that can perform actions. Only use these tools when:
        1. The user explicitly requests the action.
        2. The action is clearly the most appropriate response to their query.

        If the user asks you to perform an action, retrieve the required information from his prompt and the conversation history, then use the tool.

        If date is needed, Use today's date to make a relative date if the user didn't provide a clear one (e.g. tomorrow, in one week, etc.).
        Rarely suggest the actions in your response.
    """).strip(),
    'restrict_to_sources': dedent("""
        ## INSTRUCTIONS FOR ANSWERING QUERIES

        1. For greetings (hello, hi, how are you), reply with a greeting.

        2. For all other questions, you MUST ONLY use information from the provided context and conversation history.

        3. If the context and history don't contain information to answer the query:
           - use the assistant/user messages as context or ask the user to provide more information.
           - DO NOT make up information or use your general knowledge.

        4. When answering based on the context:
           - Synthesize information from multiple sources when appropriate
           - Consider the conversation history for follow-up questions

        5. If a user asks a follow-up question like 'what is this?' or 'tell me more', refer to the conversation history to understand the context and answer accordingly.

        6. If no context is provided at all, respond with: 'No source information has been provided for me to reference.'
    """).strip(),
    'context': dedent("""
        - Use the context to answer the question.
        - Provide references to all attachments as a new paragraph at the end of the response, listing each reference in a bullet point.
        - If your response doesn't make use of the context, don't list the attachments.
    """).strip(),
}


class AIAgent(models.Model):
    _name = 'ai.agent'
    _description = "AI Agent"
    _order = 'name'

    @api.model
    def _get_llm_model_selection(self):
        selection = []
        for available_models in SELECTION_MODELS.values():
            selection.extend(available_models)
        return selection

    name = fields.Char(string="Agent Name", related='partner_id.name', required=True, readonly=False)
    subtitle = fields.Char(string="Subtitle")
    system_prompt = fields.Text(string="System Prompt", help="Customize to control relevance and formatting.")
    response_style = fields.Selection(
        selection=[
            ('analytical', "Analytical"),
            ('balanced', "Balanced"),
            ('creative', "Creative"),
        ],
        string="Response Style",
        default='balanced',
        required=True,
    )

    llm_model = fields.Selection(
        selection=_get_llm_model_selection,
        string="LLM Model",
        default='gpt-4',
        required=True,
    )
    restrict_to_sources = fields.Boolean(
        string="Restrict to Sources",
        help="If checked, the agent will only respond based on the provided sources.")
    image_128 = fields.Image("Image", related="partner_id.image_1920", max_width=128, max_height=128, readonly=False)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ai_agent_attachment_rel',
        'agent_id',
        'attachment_id',
        string="Attachment Sources",
        index=True,
    )

    urls = fields.Text(string="URLs")
    url_attachment_ids = fields.Many2many(
        'ir.attachment',
        'ai_agent_url_attachment_rel',
        'agent_id',
        'attachment_id',
        string="URL Sources",
        index=True,
    )

    topic_ids = fields.Many2many(
        'ai.topic',
        string="Topics",
        help="A topic includes instructions and tools that guide Odoo AI in helping the user complete their tasks.",
    )
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        image_placeholder = file_open('ai/static/description/icon.png', 'rb').read()
        for vals in vals_list:
            partner = self.env['res.partner'].create({
                'name': vals.get('name'),
                'active': False,
            })
            vals['partner_id'] = partner.id
        ai_agents = super().create(vals_list)
        for agent in ai_agents:
            if agent.attachment_ids:
                agent._setup_attachment_embeddings()

            if not agent.image_128:
                agent.image_128 = base64.b64encode(image_placeholder)

            if agent.urls:
                agent._process_urls()

        return ai_agents

    def write(self, vals):
        result = super().write(vals)
        for agent in self:
            if 'attachment_ids' in vals:
                agent._setup_attachment_embeddings()

            if 'urls' in vals:
                agent._process_urls()

        return result

    @api.constrains('urls')
    def _check_url(self):
        for agent in self.filtered('urls'):
            urls = [url.strip() for url in agent.urls.split('\n') if url.strip()]
            # Allow up to 300 URLs for each agent
            if len(urls) > 300:
                raise ValidationError(_("A single agent can only have up to 300 URLs."))

            for url in urls:
                if url and not url.startswith(('https://', 'http://', 'ftp://')):
                    raise ValidationError(
                        _("URL %s does not seem complete, as it does not begin with http(s):// or ftp://", url))

    @api.onchange('attachment_ids')
    def _onchange_attachment_ids(self):
        self.ensure_one()
        if not self.attachment_ids:
            return

        unique_attachment_ids = {attachment.checksum: attachment.id for attachment in self.attachment_ids}.values()
        unique_attachments = self.attachment_ids.filtered(lambda att: att.id in unique_attachment_ids)

        valid_attachments = unique_attachments.filtered(lambda att: att.index_content and len(att.index_content.split()) > 1)
        invalid_attachments = unique_attachments - valid_attachments

        # Get existing embeddings for valid attachments
        checksums = valid_attachments.mapped('checksum')
        existing_embeddings = self.env['ai.embedding'].search([('checksum', 'in', checksums)])
        existing_embeddings_map = {emb.checksum: emb.attachment_id for emb in existing_embeddings}

        # Build final attachment list by using existing attachments with embeddings when possible
        final_attachment_ids = self.env['ir.attachment']
        for attachment in valid_attachments:
            final_attachment_ids |= existing_embeddings_map.get(attachment.checksum, attachment)

        self.attachment_ids = final_attachment_ids

        # Check for invalid attachments
        if invalid_attachments:
            attachment_names = ", ".join([attachment.name for attachment in invalid_attachments])
            invalid_pdf_attachments = invalid_attachments.filtered(lambda a: a.mimetype == 'application/pdf')
            if invalid_pdf_attachments:
                _logger.warning("Attachment indexation of PDF documents might be unavailable because the 'pdfminer' Python library cannot be found on the system. "
                                "You may install it from https://pypi.org/project/pdfminer.six/ (e.g. `pip3 install pdfminer.six`)")

            return {
                'warning': {
                    'title': _("Invalid Attachment"),
                    'message': _("%s cannot be processed to train the AI Agent. Try with different file format!", attachment_names),
                    'type': 'notification',
                }
            }

    def _setup_attachment_embeddings(self):
        self.ensure_one()
        trigger_embeddings_cron = False
        if not self.attachment_ids:
            return False

        for attachment in self.attachment_ids:
            if attachment.index_content and len(attachment.index_content.split()) > 1:
                # Check if this attachment already has embeddings
                existing = self.env['ai.embedding'].search([('checksum', '=', attachment.checksum)], limit=1)
                if not existing:
                    attachment._generate_embedding()
                    trigger_embeddings_cron = True
        if trigger_embeddings_cron:
            self.env.ref('ai.ir_cron_generate_embedding')._trigger()

    def _process_urls(self):
        """Process URLs stored in the agent's urls field.
        Before scraping, it checks if the URLs already have attachments in the db."""

        self.ensure_one()
        trigger_embeddings_cron = False
        if not self.urls:
            return False

        urls = list({url.strip() for url in self.urls.split('\n') if url.strip()})
        if not urls:
            return False

        # Identify attachments to unlink (URLs no longer in the list)
        existing_agent_attachments = self.url_attachment_ids.filtered(lambda a: a.url)
        attachments_to_unlink = existing_agent_attachments.filtered(
            lambda a: a.url not in urls
        )
        if attachments_to_unlink:
            self.write({
                'url_attachment_ids': [Command.unlink(attachment.id) for attachment in attachments_to_unlink]
            })

        # Get existing attachments if the URL already has an attachment
        existing_url_attachments = self.env['ir.attachment'].search([
            ('url', 'in', urls),
            ('res_model', '=', 'ai.agent')
        ])

        # Create a dictionary mapping URLs to existing attachments
        existing_url_map = {attachment.url: attachment for attachment in existing_url_attachments}
        scraper = URLScraper()
        failed_urls = []

        for url in urls:
            # Check if URL already has an attachment
            if url in existing_url_map:
                # Map existing attachment to this agent
                existing_attachment = existing_url_map[url]
                if existing_attachment.id not in self.url_attachment_ids.ids:
                    self.write({
                        'url_attachment_ids': [Command.link(existing_attachment.id)]
                    })
                continue

            # If URL doesn't have an attachment, scrape and create new one
            result = scraper.scrap(url)
            if not result or not result['content']:
                _logger.warning("No content retrieved from URL %s", url)
                failed_urls.append(url)
                continue

            # Create attachment with URL content
            attachment_values = {
                'name': f"{result['title']}-({url})",
                'res_model': 'ai.agent',
                'res_id': self.id,
                'type': 'url',
                'index_content': result['content'],
                'mimetype': 'text/html',
                'url': url
            }

            new_attachment = self.env['ir.attachment'].create(attachment_values)
            new_attachment._generate_embedding()
            self.write({
                'url_attachment_ids': [Command.link(new_attachment.id)]
            })
            trigger_embeddings_cron = True

        if trigger_embeddings_cron:
            self.env.ref('ai.ir_cron_generate_embedding')._trigger()

        if failed_urls:
            failed_urls_str = ", ".join(failed_urls)
            raise UserError(_("The following URLs cannot not be accessed or used for the agent: %s", failed_urls_str))

    def get_document_stats(self):
        self.ensure_one()
        all_attachments = self.attachment_ids + self.url_attachment_ids
        n_docs = len(all_attachments)
        if not n_docs:
            return {
                'show_alert': False
            }
        self.env.cr.execute(SQL(
            '''
                SELECT COUNT(DISTINCT attachment_id)
                FROM ai_embedding
                WHERE attachment_id = ANY(%s) AND embedding_vector IS NOT NULL
            ''', all_attachments.ids)
        )
        processed_count = self.env.cr.fetchall()[0][0]
        percentage = int(processed_count / n_docs * 100) if n_docs else 0

        cron = self.env.ref('ai.ir_cron_generate_embedding')
        last_cron_time = cron.lastcall

        if not last_cron_time or last_cron_time < fields.Datetime.now() - timedelta(minutes=3):
            self.env.ref('ai.ir_cron_generate_embedding')._trigger()

        return {
            'percentage': percentage,
        }

    def generate_response(self, prompt: str):
        for agent in self:
            prompt = html_to_inner_content(prompt)
            channel = self.env['discuss.channel']._get_or_create_chat([
                self.env.user.partner_id.id,
                agent.partner_id.id
            ])

            response = self._generate_response(
                prompt=prompt,
                ai_agent=agent,
                discuss_channel_id=channel,
            )
            for message in response or []:
                formatted_message = message
                if markdown:
                    raw_html = markdown(message, extras=['fenced-code-blocks', 'tables', 'strike'])
                    formatted_message = Markup(html_sanitize(raw_html))
                channel.sudo().message_post(
                    author_id=agent.partner_id.id,
                    body=formatted_message,
                    message_type='comment',
                    silent=True,
                    subtype_xmlid='mail.mt_comment'
                )

    def open_agent_chat(self):
        self.ensure_one()
        channel = self.env['discuss.channel']._get_or_create_chat([
            self.env.user.partner_id.id,
            self.partner_id.id,
        ])

        return {
            'type': 'ir.actions.client',
            'tag': 'agent_chat_action',
            'params': {
                'channelId': channel.id,
            },
        }

    def _generate_response(self, prompt, ai_agent, discuss_channel_id):
        response_temperature = TEMPERATURE_MAP[ai_agent.response_style]
        chat_history = self._retrieve_chat_history(discuss_channel_id)
        messages = self._prepare_chat_messages(prompt=prompt, ai_agent=ai_agent)

        full_conversation = chat_history + messages
        functions_descriptions = self._generate_functions_descriptions(ai_agent.topic_ids)
        provider = next((provider for provider, models in PROVIDERS_MODELS.items() if self.llm_model in models), None)
        if not provider:
            raise UserError(_("No provider found for the selected model"))

        api_service = LLMApiService(env=self.env, provider=provider)
        api_response = api_service.get_completion(
            model=self.llm_model,
            messages=full_conversation,
            tools=functions_descriptions,
            temperature=response_temperature,
        )

        if api_response:
            response_messages = []

            response_processed = False
            while not response_processed:
                # Process the API response
                api_response = api_response['choices'][0]['message']
                response_processed = True
                full_conversation.append(api_response)
                if api_response.get('content'):
                    response_messages.append(api_response['content'])
                # Check if the response contains a tool to call
                if api_response.get('tool_calls'):
                    messages = self._use_tools(tools_to_use=api_response['tool_calls'], topic_ids=ai_agent.topic_ids)
                    full_conversation.extend(messages)
                    api_response = api_service.get_completion(
                        model=self.llm_model,
                        messages=full_conversation,
                        temperature=response_temperature)
                    response_processed = False
            return response_messages

    def _retrieve_chat_history(self, discuss_channel_id, no_messages=20):
        chat_history = [
            {
                'content': message.body,
                'role': 'assistant' if message.author_id.agent_ids else 'user'
            }
            for message in discuss_channel_id.message_ids[:no_messages]
        ]

        chat_history.reverse()
        return chat_history

    def _prepare_chat_messages(self, prompt, ai_agent):
        today_date = fields.Date.context_today(self)
        system_content = ai_agent.system_prompt or "You are a RAG assistant."
        system_content += f"\n\nToday's date to be used: {today_date}"

        if ai_agent.topic_ids:
            system_content += PREPROMPTS['tools']

        messages = [{'role': 'system', 'content': system_content}]

        if ai_agent.topic_ids:
            topic_instructions = "\n\n".join(
                [topic.instructions for topic in ai_agent.topic_ids if topic.instructions])
            if topic_instructions:
                messages.append(
                    {'role': 'system', 'content': f"Additional topic instructions:\n{topic_instructions}."})

        context = ""
        all_attachments = ai_agent.attachment_ids + ai_agent.url_attachment_ids
        if all_attachments:
            response = LLMApiService(env=self.env, provider='openai').get_embedding(input=prompt)
            prompt_embedding = response['data'][0]['embedding']
            similar_embeddings = ai_agent.env['ai.embedding']._get_similar_chunks(
                query_embedding=prompt_embedding,
                attachment_ids=all_attachments.ids,
                top_n=5
            )
            if similar_embeddings:
                referenced_attachments = set()
                for embedding in similar_embeddings:
                    context += f"{embedding.attachment_id.name}\n{embedding.content}\n\n"
                    if embedding.attachment_id and embedding.attachment_id.name:
                        referenced_attachments.add(embedding.attachment_id.name)
                context += f"##References:\n{', '.join(referenced_attachments)}"

        if ai_agent.restrict_to_sources:
            messages.append({
                'role': 'system',
                'content': PREPROMPTS['restrict_to_sources']
            })

        if context:
            messages.append(
                {'role': 'user', 'content': f"##Context information:\n\n{context}\n{PREPROMPTS['context']}"})

        messages.append({'role': 'user', 'content': prompt})
        return messages

    def _generate_functions_descriptions(self, topic_ids):
        functions_descriptions = []
        for topic in topic_ids:
            for ai_tool in topic.tool_ids:
                ai_tool_input_schema = json.loads(ai_tool.input_schema)
                functions_descriptions.append({
                    'type': 'function',
                    'function': {
                        'name': ai_tool.formatted_name,
                        'description': ai_tool.description,
                        'parameters': {
                            'type': 'object',
                            'properties': self._extract_property_values(
                                ai_tool_input_schema['properties'],
                                property_values_to_extract=['type', 'description']
                            ),
                            'required': list(ai_tool_input_schema['properties'].keys()),
                            'additionalProperties': False
                        },
                        'strict': True
                    }
                })
        return functions_descriptions

    def _extract_property_values(self, ai_tool_properties, property_values_to_extract):
        properties = defaultdict(defaultdict)
        for property_name in ai_tool_properties:
            for value in property_values_to_extract:
                properties[property_name][value] = ai_tool_properties[property_name][value]
        return properties

    def _use_tools(self, tools_to_use, topic_ids):
        tool_map = {}
        for ai_tool in topic_ids.tool_ids:
            tool_map[ai_tool.formatted_name] = ai_tool

        tools_usage_results = []
        for tool_to_use in tools_to_use:
            tool_title = tool_to_use['function']['name']
            tool_arguments = json.loads(
                tool_to_use['function']['arguments'])
            ai_tool = tool_map[tool_title]
            tools_usage_results.append({
                'role': 'tool',
                'tool_call_id': tool_to_use['id'],
                'content': ai_tool._use_tool(tool_arguments)
            })
        return tools_usage_results

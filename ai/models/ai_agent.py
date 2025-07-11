# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import lxml.html
import copy

from datetime import timedelta
from textwrap import dedent
try:
    from markdown2 import markdown
except ImportError:
    markdown = None

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import file_open, html_sanitize, SQL, is_html_empty
from odoo.tools.mail import html_to_inner_content

from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.ai.utils.url_scraping import URLScraper
from odoo.addons.ai.utils.tools_schema.tools import call_ai_tool

_logger = logging.getLogger(__name__)

# Pre-prompts and constants
SELECTION_MODELS = {
    'openai': [('gpt-3.5-turbo', "GPT-3.5 Turbo"), ('gpt-4', "GPT-4"), ('gpt-4o', "GPT-4o"), ('gpt-4.1', "GPT-4.1"), ('gpt-4.1-mini', "GPT-4.1 Mini")],
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
        default='gpt-4o',
        required=True,
    )
    restrict_to_sources = fields.Boolean(
        string="Restrict to Sources",
        help="If checked, the agent will only respond based on the provided sources.")
    image_128 = fields.Image("Image", related="partner_id.image_1920", max_width=128, max_height=128, readonly=False)
    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string="Attachment Sources",
        domain=[('url', '=', False)],
    )

    urls = fields.Text(string="URLs")
    url_attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        string="URL Sources",
        domain=[('url', '!=', False)],
    )

    attachment_processing_percentage = fields.Integer(compute="_compute_attachment_processing_percentage", default=100)

    topic_ids = fields.Many2many(
        'ai.topic',
        string="Topics",
        help="A topic includes instructions and tools that guide Odoo AI in helping the user complete their tasks.",
    )
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    is_system_agent = fields.Boolean('System Agent', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        with file_open('ai/static/description/icon.png', 'rb') as f:
            image_placeholder = f.read()
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
        if 'partner_id' in vals:
            raise ValidationError(_("The partner linked to an AI agent can't be changed"))

        result = super().write(vals)
        for agent in self:
            if 'attachment_ids' in vals:
                agent._setup_attachment_embeddings()

            if 'urls' in vals:
                agent._process_urls()

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_system_agent(self):
        """Prevent deletion of system agents."""
        system_agents = self.filtered('is_system_agent')
        if system_agents:
            raise UserError(_("System agents cannot be deleted."))

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

        self.attachment_ids = valid_attachments

        # Check for invalid attachments
        if invalid_attachments:
            attachment_names = ", ".join([attachment.name for attachment in invalid_attachments])

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
                existing = self.env['ai.embedding'].search([('attachment_id', '=', attachment.id)], limit=1)
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

    def action_refresh(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            return

        cron = self.env.ref('ai.ir_cron_generate_embedding')
        last_cron_time = cron.lastcall

        if not last_cron_time or last_cron_time < fields.Datetime.now() - timedelta(minutes=3):
            self.env.ref('ai.ir_cron_generate_embedding')._trigger()

    def get_direct_response(self, prompt: str, context_message: str = ""):
        """Get a direct response from the agent's provider LLM without chat history or channel creation."""
        self.ensure_one()
        response = self._generate_response(prompt=prompt, extra_system_context=context_message)
        return response

    def generate_response(self, mail_message_id: int):
        self.ensure_one()
        mail_message = self.env['mail.message'].browse(mail_message_id).exists()
        if not mail_message:
            raise UserError(_("The message does not exist or has been deleted."))

        prompt = html_to_inner_content(mail_message.body)
        channel = self.env['discuss.channel']._get_or_create_ai_chat(self.partner_id)
        response = self._generate_response(prompt=prompt, chat_history=self._retrieve_chat_history(channel))
        for message in response or []:
            self._post_ai_response(channel, message)

    def post_error_message(self, error_message: str):
        self.ensure_one()
        channel = self.env['discuss.channel']._get_or_create_ai_chat(self.partner_id)
        response = self._generate_response(
            prompt="Generate a message for the user stating that we are unable to process the request because of the following error: " + error_message,
            chat_history=self._retrieve_chat_history(channel),
            extra_system_context="Do not mention any technical terms or error codes in the generated message but be precise because the generated message will be used as info for potential retries of the request.")
        for message in response or []:
            self._post_ai_response(channel, message)

    def open_agent_chat(self):
        self.ensure_one()
        channel = self.env['discuss.channel']._get_or_create_ai_chat(self.partner_id)
        return {
            'type': 'ir.actions.client',
            'tag': 'agent_chat_action',
            'params': {
                'channelId': channel.id,
            },
        }

    def close_chat(self, channel_id: int):
        self.ensure_one()
        channel = self.env['discuss.channel'].search([
            ('id', '=', channel_id),
            ('is_member', '=', True),
            ('channel_type', '=', 'ai_chat')
        ])
        if channel:
            channel.sudo().unlink()

    def _post_ai_response(self, channel, message):
        formatted_message = message
        if markdown:
            raw_html = markdown(message, extras=['fenced-code-blocks', 'tables', 'strike'])
            formatted_message = html_sanitize(raw_html)
        channel.sudo().message_post(
            author_id=self.partner_id.id,
            body=formatted_message,
            message_type='comment',
            silent=True,
            subtype_xmlid='mail.mt_comment'
        )

    def _get_openai_compatible_schema(self, schema):
        input_schema = copy.deepcopy(schema["parameters"])
        input_schema_properties = input_schema["properties"]
        required_parameters = input_schema["required"]
        for param_name, param_definition in input_schema_properties.items():
            param_type = input_schema_properties[param_name]["type"]
            # OpenAI function calling strict mode https://platform.openai.com/docs/guides/function-calling#strict-mode
            # According to OpenAI docs on strict mode "Setting strict to true will ensure function calls reliably adhere
            # to the function schema, instead of being best effort. We recommend always enabling strict mode."
            # In strict mode, all parameters should be set as required. To denote that a parameter is optional,
            # we set its type to 'anyOf' the original type or 'null'. So {'type': 'string'} becomes 'anyOf': [{'type': 'string'}, {'type': 'null'}].
            # However, if the parameter type is object, it cannot be optional i.e. 'anyOf': [{'type': 'object'}, {'type': 'null'}].
            # For an object parameter, the required attribute must be defined as a list of the names of the required properties of the object.
            # i.e. 'required': [<property1_name>, <property2_name>, ..]. If the whole object is optional, required is set to an empty list  'required': []
            if param_type != "object" and param_name not in required_parameters:
                input_schema_properties[param_name]["anyOf"] = [
                    {"type": param_type},
                    {"type": "null"},
                ]
                input_schema_properties[param_name].pop("type")

            # Openai function calling api doesn't support 'pattern' attribute
            param_definition.pop("pattern", None)

            if param_type == 'object':
                object_required_properties = param_definition['required']
                for property_name, property_definition in param_definition['properties'].items():
                    if property_name not in object_required_properties:
                        property_definition["anyOf"] = [
                            {"type": property_definition['type']},
                            {"type": "null"},
                        ]
                        property_definition.pop("type")

                    property_definition.pop("pattern", None)

        # For any object, all properties should be set as required.
        for property_attributes in input_schema_properties.values():
            if property_attributes.get("type") == "object":
                property_attributes["additionalProperties"] = False
                property_attributes["required"] = list(
                    property_attributes["properties"].keys()
                )

        input_schema["required"] = list(input_schema_properties.keys())
        openai_formatted_tool_description = {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": {
                    **input_schema,
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
        return openai_formatted_tool_description

    def _get_available_ai_tools(self, provider):
        tools = [*self.topic_ids.tool_ids.mapped('schema')]
        if provider == 'openai':
            return [self._get_openai_compatible_schema(tool["function"]) for tool in tools]
        return tools

    def _generate_response(self, prompt, chat_history=None, extra_system_context=""):
        self.ensure_one()
        response_temperature = TEMPERATURE_MAP[self.response_style]
        system_messages = self._build_system_context(extra_system_context=extra_system_context)
        if rag_context := self._build_rag_context(prompt):
            system_messages.extend(rag_context)
        full_conversation = system_messages + (chat_history or []) + [{'role': 'user', 'content': prompt}]
        provider = next((provider for provider, models in PROVIDERS_MODELS.items() if self.llm_model in models), None)
        if not provider:
            raise UserError(_("No provider found for the selected model"))

        available_tools = self._get_available_ai_tools(provider)
        api_service = LLMApiService(env=self.env, provider=provider)
        api_response = api_service.get_completion(
            model=self.llm_model,
            messages=full_conversation,
            tools=available_tools,
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
                    tool_call_messages = [
                        call_ai_tool(self.env['ai.tool'], tool_call)
                        for tool_call in api_response['tool_calls']
                    ]
                    full_conversation.extend(tool_call_messages)
                    api_response = api_service.get_completion(
                        model=self.llm_model,
                        messages=full_conversation,
                        tools=available_tools,
                        temperature=response_temperature)
                    response_processed = False
            return response_messages

    def _retrieve_chat_history(self, discuss_channel, no_messages=20):
        chat_history = [
            {
                'content': message.body,
                'role': 'assistant' if message.author_id.agent_ids else 'user'
            }
            for message in discuss_channel.message_ids[:no_messages]
        ]

        chat_history.reverse()
        return chat_history

    def _build_system_context(self, extra_system_context: str = ""):
        self.ensure_one()
        today_date = fields.Date.context_today(self)
        system_content = self.system_prompt or "You are a RAG assistant."
        system_content += f"\n\nToday's date to be used: {today_date}"

        if self.topic_ids:
            system_content += PREPROMPTS['tools']

        messages = [{'role': 'system', 'content': system_content}]

        if self.topic_ids:
            topic_instructions = "\n\n".join(
                [topic.instructions for topic in self.topic_ids if topic.instructions])
            if topic_instructions:
                messages.append(
                    {'role': 'system', 'content': f"Additional topic instructions:\n{topic_instructions}."})

        if self.restrict_to_sources:
            messages.append({
                'role': 'system',
                'content': PREPROMPTS['restrict_to_sources']
            })

        if extra_system_context:
            messages.append({'role': 'system', 'content': extra_system_context})

        return messages

    def _build_rag_context(self, prompt):
        self.ensure_one()
        messages = []
        context = ""
        all_attachments = self.attachment_ids + self.url_attachment_ids
        if all_attachments:
            response = LLMApiService(env=self.env, provider='openai').get_embedding(input=prompt)
            prompt_embedding = response['data'][0]['embedding']
            similar_embeddings = self.env['ai.embedding']._get_similar_chunks(
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

        if context:
            messages.append({'role': 'system', 'content': f"##Context information:\n\n{context}\n{PREPROMPTS['context']}"})
        return messages

    @api.depends("attachment_ids", "url_attachment_ids")
    def _compute_attachment_processing_percentage(self):
        for record in self:
            all_attachments = record.attachment_ids + record.url_attachment_ids
            n_docs = len(all_attachments)
            if not n_docs:
                record.attachment_processing_percentage = 100

            self.env.cr.execute(SQL(
                '''
                    SELECT COUNT(DISTINCT attachment_id)
                    FROM ai_embedding
                    WHERE attachment_id = ANY(%s) AND embedding_vector IS NOT NULL
                ''', all_attachments.ids)
            )
            processed_count = self.env.cr.fetchall()[0][0]
            percentage = int(processed_count / n_docs * 100) if n_docs else 0

            record.attachment_processing_percentage = percentage

    def _eval_ai_prompts(self, rendered_html, remove_prompts=False, ai_context=""):
        """Evaluate AI prompts in the given HTML content"""
        if is_html_empty(rendered_html):
            return rendered_html

        Wrapper = rendered_html.__class__
        root = lxml.html.fromstring(rendered_html)

        prompt_containers = root.xpath("//div[hasclass('o_editor_prompt')]")

        if not prompt_containers:
            return Wrapper(rendered_html)

        for container in prompt_containers:
            prompt_content_elements = container.xpath(
                ".//div[hasclass('o_editor_prompt_content')]"
            )

            if remove_prompts:
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

            response = self._generate_response(prompt_text, extra_system_context=ai_context)

            if not response:
                container.getparent().remove(container)
                continue

            # Wrapped each line of the response in a <p> tag.
            wrapped_content = "\n".join(f"<p>{content}</p>" for content in response[0].split("\n") if content.strip())
            replacement_html_str = html_sanitize(wrapped_content, sanitize_attributes=True, sanitize_style=True)
            container.getparent().replace(container, lxml.html.fromstring(replacement_html_str))

        return Wrapper(lxml.html.tostring(root, encoding="unicode", method="html"))

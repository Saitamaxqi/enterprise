# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pytz
import requests
from datetime import datetime
from dateutil.parser import isoparse
from markupsafe import Markup

try:
    from markdown2 import markdown
except ImportError:
    markdown = None
from lxml import html

from odoo import fields
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.exceptions import UserError
from odoo.tools import html_sanitize
from odoo.tools.mail import html_to_inner_content

AI_FIELDS_INSTRUCTIONS = """# Identity
You are an intelligent assistant integrated into an ERP system, specializing in generating accurate and relevant values for various data fields.

# Instructions
Your task is to resolve a single value for a specific ERP field based on the user's request or value description.

## Input Format
You will receive free-text prompts referring to ERP-related entities, values, or attributes, which may contain:
- Field references: {{field_path}} - their values are added in a context dict, provided below
- A context dict: it is an ORM snapshot that has the following structure:
    {
        <model_name>: [
                'id': <record_id>
                <field_name>: value | {'model': <model_name>, 'ids': [<res_id>]}
            ]
        }
    }
Where {'model': <model_name>, 'ids': [<res_id>]} are relational values and <file_#idx> refers to the additional inputs in the input array.

## Output Format
You must return a structured output:
- `value`: the value to assign.
- `could_not_resolve`: `true` if the value is missing, unverifiable, or cannot be determined reliably
- `unresolved_cause`: a brief explanation if the request could not be resolved

## Rules
- Rely on internal knowledge only for unchanging historical facts. In all other cases, do a web search to retrieve the necessary information.
- After searching, make sure the results truly match the user's request. If not, set `could_not_resolve` to `true`.
- Do not guess, fabricate, or complete missing information based on assumptions. If a value cannot be determined reliably, set `could_not_resolve` to `true`.
- Never include internal field names, record IDs, or system-specific labels in your final value.
- Before resolving any value, verify that the entity (company, product, location, or other referenced subject) exists in reality or is verifiable.
- If the entity is fictional, unknown, or unverifiable, do not attempt to guess or fabricate any values.
- In such cases, set `value: null`, `could_not_resolve: true`, and include a `resolution_note`.
"""

OPENAI_ENDPOINT = '/responses'
OPENAI_MODEL = 'gpt-4.1'  # prompts are usually tweaked for a model. Double check behavior if changed.


class UnresolvedQuery(UserError):
    pass


def get_ai_value(record, field_type, user_prompt, context_fields, allowed_values):
    """Query a LLM with the given prompt and return the cast value.

    :param record: the record for which the value should be obtained
    :param field_type: the field type for which the response should be cast
    :param user_prompt: the "user prompt" to pass to the LLM (the request)
    :param context_fields: list of field paths that needs to be included in the context dict
    :param allowed_values: a dict containing the values that are allowed

    :return: the value with the type expected for the given field type, or False if the value
        could not be cast or is not in allowed_values
    """
    if field_type in ('many2many', 'many2one', 'selection', 'tags') and not allowed_values:
        raise UnresolvedQuery(record.env._("No allowed values are provided in the prompt."))
    context_dict, files = record._get_ai_context(context_fields)
    llm_api = LLMApiService(record.env, 'openai')
    if field_type == 'boolean':
        schema = {
            'type': 'boolean',
        }
    elif field_type == 'char':
        schema = {
            'type': 'string',
            'description': 'A short, concise string, without any Markdown formatting.'
        }
    elif field_type == 'date':
        schema = {
            'type': ['string', 'null'],
            'format': 'date',
            'description': 'A date (year, month and day should be correct), or null to leave empty',
        }
    elif field_type == 'datetime':
        schema = {
            'type': ['string', 'null'],
            'format': 'date-time',
            'description': 'A datetime (year, month and day should be correct), including the correct timezone or null to leave empty'
        }
    elif field_type == 'integer':
        schema = {
            'type': 'integer',
            'description': "A whole number. If a number is expressed in words (e.g. '6.67 billion'), it must be converted into its full numeric form (e.g. '6670000000')"
        }
    elif field_type in ('float', 'monetary'):
        schema = {
            'type': 'number'
        }
    elif field_type == 'html':
        schema = {
            'type': 'string',
            'description': 'A well-structured Markdown (it may contain tables). It will be converted to HTML after generation'
        }
    elif field_type == 'text':
        schema = {
            'type': 'string',
            'description': 'A few sentences, without any Markdown formatting'
        }
    elif field_type == 'many2many':
        schema = {
            'type': 'array',
            'items': {
                'type': 'integer',
                'enum': list(allowed_values)
            },
            'description': 'The list of IDs of records to select. Leave empty to leave the field empty'
        }
    elif field_type == 'many2one':
        schema = {
            'type': ['integer', 'null'],
            'enum': list(allowed_values) + [None],
            'description': 'The ID of the record to select. null to leave the field empty if no value matches the user query'
        }
    elif field_type == 'selection':
        schema = {
            'type': ['string', 'null'],
            'enum': list(allowed_values) + [None],
            'description': 'Key of the value to select. null to leave the field empty'
        }
    elif field_type == 'tags':
        schema = {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': list(allowed_values)
            },
            'description': 'List of keys of the tags to select. Leave empty to leave the field empty'
        }
    else:
        schema = {'type': 'text'}

    instructions = f"{AI_FIELDS_INSTRUCTIONS}\n# Context"
    if allowed_values:
        instructions += f"\n## Allowed Values\n{json.dumps(allowed_values)}"
    instructions += f"\n The current date is {datetime.now(pytz.utc).astimezone().replace(second=0, microsecond=0).isoformat()}"

    if context_dict:
        user_prompt += f"\n# Context Dict\n{json.dumps(context_dict, ensure_ascii=False, indent=2)}"
        user_prompt += f"\nThe current record is {{'model': {record._name}, 'id': {record._origin.id}}}"

    web_search_params = {
        'user_location':
        {
            'type': 'approximate',
            'country': country_code,
            'city': record.env.company.partner_id.city,
        }
    } if (country_code := record.env.company.country_id.code) else {}

    try:
        # TODO: remove and use `_request_llm`
        llm_response = llm_api._request(
            'post',
            OPENAI_ENDPOINT,
            llm_api._get_base_headers(),
            body={
                'model': OPENAI_MODEL,
                'instructions': instructions,
                'input': [{
                    'role': 'user',
                    'content': [
                        {'type': 'input_text', 'text': user_prompt},
                        *(
                            {'type': 'input_file', 'filename': f"file_{idx}.pdf", 'file_data': f"data:{file['mimetype']};base64,{file['value']}"}
                            if file['mimetype'] == 'application/pdf' else
                            {'type': 'input_image', 'image_url': f"data:{file['mimetype']};base64,{file['value']}", 'detail': 'low'}
                            if file['mimetype'].startswith("image/") else
                            {'type': 'input_text', 'text': file['value']}
                            for idx, file in enumerate(files, start=1)
                        )
                    ]
                }],
                'store': False,
                'temperature': 0.2,
                'text': {
                    'format': {
                        'type': 'json_schema',
                        'description': 'Value to assign to the field',
                        'name': 'generate_field_value',
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'value': schema,
                                'could_not_resolve': {
                                    'type': 'boolean',
                                    'description': 'True if the model could not confidently determine a value due to missing information, ambiguity, or unknown references in the input.'
                                },
                                'unresolved_cause': {
                                    'type': ['string', 'null'],
                                    'description': 'Short explanation of what is missing or why no value could be generated. Required if could_not_resolve is true.'
                                },
                            },
                            'required': ['value', 'could_not_resolve', 'unresolved_cause'],
                            'additionalProperties': False
                        },
                        'strict': True
                    }
                },
                'tools': [{
                    'type': 'web_search_preview',
                    **web_search_params,
                }],
            }
        )
    except requests.exceptions.Timeout:
        raise UserError(record.env._("Oops, the request timed out."))
    except requests.exceptions.ConnectionError:
        raise UserError(record.env._("Oops, the connection failed."))

    if (error := llm_response.get('error')):
        raise UserError(error.get('message'))

    if (
        not (output := llm_response.get('output'))
        or not (content := output[-1].get('content'))
        or not (response := content[0].get('text'))
        ):
        raise UserError(record.env._("Oops, an unexpected error occurred."))

    try:
        response = json.loads(response, strict=False)
    except json.JSONDecodeError:
        raise UserError(record.env._("Oops, the response could not be processed."))
    if response.get('could_not_resolve'):
        raise UnresolvedQuery(response.get('unresolved_cause'))

    return parse_ai_response(
        response.get('value'),
        field_type,
        allowed_values,
    )


def get_field_prompt_vals(env, field, field_prompt=None):
    """Get the allowed values for the given field.

    :param field: the field from which to obtain the allowed values

    :return: The allowed values if the field requires specific values
    """
    user_prompt, fields, allowed_values = parse_ai_prompt_values(env, field_prompt or field.ai, field.comodel_name)
    if field.type == 'selection':
        allowed_values = field._selection
    return user_prompt, fields, allowed_values  # do we need html_to_inner_content?


def get_property_prompt_vals(env, property_definition):
    """Get the allowed values for the given property field.

    :param property_definition: the property definition from which to obtain the allowed values

    :return: the allowed values if the property requires specific values
    """
    property_type = property_definition.get('type')
    user_prompt = property_definition.get('system_prompt')
    user_prompt, fields, allowed_values = parse_ai_prompt_values(env, user_prompt, property_definition.get('comodel'))
    if property_type == 'selection':
        allowed_values = dict(property_definition.get('selection', {}))
    elif property_type == 'tags':
        allowed_values = {name: label for name, label, color in (property_definition.get('tags') or [])}
    return user_prompt, fields, allowed_values  # do we need html_to_inner_content?


def parse_ai_prompt_values(env, prompt, comodel, replace_prompt=True):
    fields = set()
    records = set()
    tree = html.fromstring(prompt)

    for el in tree.xpath('//span[@data-ai-field]'):
        field_path = el.attrib.get('data-ai-field')
        if replace_prompt:
            if field_path:
                el.text = f"{{{{{field_path}}}}}"
            else:
                el.drop_tree()
        fields.add(field_path)

    if comodel:
        els = tree.xpath('//span[@data-ai-record-id]')
        records = {int(i) for el in els if (i := el.attrib.get('data-ai-record-id'))}
        if replace_prompt:
            records = {r.id: r for r in env[comodel].browse(records).exists()}
            for el in els:
                if record := records.get(int(el.attrib.get('data-ai-record-id'))):
                    el.text = record.display_name
                else:
                    el.drop_tree()

            records = env[comodel].browse(records)._ai_format_records()

    if replace_prompt:
        return html_to_inner_content(html.tostring(tree, encoding='unicode')), fields, records
    return prompt, fields, records


def parse_ai_response(response, field_type, allowed_values):
    """Parse and cast a LLM response into the type expected for the given field type and checks
    that the value is in the set of allowed_values if given.

    :param response: a LLM response
    :param str field_type: the type of the field for which the response should be cast
    :param set allowed_values: a set of values that are allowed

    :return: the value with the type expected for the given field type, or False if the value
        could not be cast or is not in allowed_values
    """
    if not allowed_values:
        allowed_values = {}

    if field_type == 'datetime':
        if not response:
            return False
        try:
            return fields.Datetime.to_string(isoparse(response).astimezone(pytz.utc))
        except ValueError:
            return False
        return response
    elif field_type == 'date':
        if not response:
            return False
        try:
            return fields.Datetime.to_string(isoparse(response))
        except ValueError:
            return False
        return response
    elif field_type in ('selection', 'many2one'):
        return response if response in allowed_values else False
    elif field_type in ('tags', 'many2many'):
        return [value for value in response if value in allowed_values]
    elif field_type == 'html':
        if markdown:
            raw_html = markdown(response, extras=['fenced-code-blocks', 'tables', 'strike']).rstrip('\n')
            return html_sanitize(raw_html or "")
        return html_sanitize(response or "")
    else:
        return response


def ai_field_insert(field_path, field_label):
    return Markup('<span data-ai-field="%s">%s</span>') % (field_path, field_label)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pytz
import re
from datetime import datetime
from dateutil.parser import isoparse
try:
    from markdown2 import markdown
except ImportError:
    markdown = None

from odoo import fields
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.tools import html_sanitize
from odoo.tools.mail import html_to_inner_content

FIELD_PROMPTS = {
    'boolean': "The field is a boolean.",
    'char': "The field is a char.",
    'date': "The field is a date.",
    'datetime': "The field is a datetime.",
    'float': "The field is a float.",
    'html': "The field is a HTML.",
    'integer': "The field is an integer.",
    'many2many': "The field is a multi-relation field (multiple records can be assigned to the field). You will receive valid records in the form: {id: Description}.",
    'many2one': "The field is a relational field. You will receive valid records in the form: {id: Description}.",
    'monetary': "The field is a monetary.",
    'selection': "The field is a selection. Only the keys from the dictionary below which maps selection values to their display name, are valid values.",
    'tags': "The field is a tags selection. Only the keys from the dictionary below which maps tags to their display names are valid values.",
    'text': "The field is a multi-line text."
}

GENERIC_PROMPT = """You are a field value generator for an ERP system. You must provide the appropriate value for a specific field (which might be to leave the field empty)."""

OPENAI_ENDPOINT = '/v1/responses'
OPENAI_MODEL = 'gpt-4.1-mini'


def get_ai_value(env, field_type, system_prompt, user_prompt, allowed_values):
    """Query a LLM with the given prompts and return the cast value.

    :param field_type: the field type for which the response should be cast
    :param system_prompt: the "system" prompt to pass to the LLM
    :param user_prompt: the "user" prompt to pass to the LLM
    :param allowed_values: as set containing the values that are allowed

    :return: the response of the LLM cast to the expected type if the value is allowed
    """
    llm_api = LLMApiService(env, 'openai')
    web_search_params = {
        'user_location':
        {
            'type': 'approximate',
            'country': country_code,
            'city': env.company.partner_id.city,
        }
    } if (country_code := env.company.country_id.code) else {}

    schema_value = {"type": "string"}
    if field_type == 'boolean':
        schema_value['type'] = 'boolean'
    elif field_type == 'char':
        schema_value['description'] = 'A short, concise string, without any Markdown formatting'
    elif field_type == 'date':
        schema_value['type'] = ['string', 'null']
        schema_value['format'] = 'date'
        schema_value['description'] = 'A full date (year, month and day should be correct). null to leave empty'
    elif field_type == 'datetime':
        schema_value['type'] = ['string', 'null']
        schema_value['format'] = 'date-time'
        schema_value['description'] = 'A full datetime (year, month and day should be correct), including the correct timezone'
    elif field_type == 'integer':
        schema_value['type'] = 'integer'
        schema_value['description'] = "A whole number. If a number is expressed in words (e.g. '6.67 billion'), it must be converted into its full numeric form (e.g. '6670000000')"
    elif field_type in ('float', 'monetary'):
        schema_value['type'] = 'number'
    elif field_type == 'html':
        schema_value['description'] = 'A well-structured Markdown (it may contain tables). It will be converted to HTML after generation'
    elif field_type == 'many2many':
        schema_value['type'] = 'array'
        schema_value['items'] = {'type': 'integer'}
        schema_value['description'] = 'The list of IDs of records to select. Leave empty to leave the field empty'
    elif field_type == 'many2one':
        schema_value['type'] = ['integer', 'null']
        schema_value['description'] = 'The ID of the record to select. null to leave the field empty'
    elif field_type == 'selection':
        schema_value['type'] = ['string', 'null']
        schema_value['description'] = "Key of the value to select. null to leave the field empty"
    elif field_type == 'tags':
        schema_value['type'] = 'array'
        schema_value['items'] = {'type': 'string'}
        schema_value['description'] = "List of keys of the tags to select. Leave empty to leave the field empty"
    elif field_type == 'text':
        schema_value['description'] = 'A few sentences, without any Markdown formatting'

    llm_response = llm_api._request(
        'post',
        OPENAI_ENDPOINT,
        llm_api._get_base_headers(),
        body={
            'model': OPENAI_MODEL,
            'instructions': f"{system_prompt}\n# Context\nThe current date is {datetime.now(pytz.utc).astimezone().isoformat()}.",
            'input': user_prompt,
            'text': {
                'format': {
                  'type': 'json_schema',
                  'description': 'Generate a value for a field',
                  'name': 'generate_field_value',
                  'schema': {
                    'type': 'object',
                    'properties': {
                      'value': schema_value
                    },
                    'required': [
                      'value'
                    ],
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

    if (
        not llm_response
        or llm_response.get('error')
        or not (output := llm_response.get('output'))
        or not (content := output[-1].get('content'))
        or not (response := content[0].get('text'))
        ):
        return False

    return parse_ai_response(
        json.loads(response, strict=False).get('value'),
        field_type,
        allowed_values,
    )


def get_field_system_prompt(env, field, field_prompt=None):
    """Get the system prompt to pass to the LLM and the allowed values for the given field.
    This prompt is common for each record of the given field and defines the role, tone and
    constraints that the LLM should adhere to.

    :param field: the field from which to obtain the system prompt and allowed values

    :return (str, set): The field's system prompt and the set of allowed values if the field
        requires specific values
    """
    field_type = field.type
    prompt = GENERIC_PROMPT + FIELD_PROMPTS[field_type]
    if field_type == 'selection':
        selection = field._selection
        return prompt + str(selection), set(selection.keys())
    elif field_type in ('many2one', 'many2many'):
        records = parse_ai_prompt_records(env, field_prompt or field.ai, field.comodel_name)
        return prompt, records
    return prompt, False


def get_property_system_prompt(env, property_definition):
    """Get the system prompt to pass to the LLM and the allowed values for the given property
    definition. This prompt is common for each record of the given field and defines the role,
    tone and constraints that the LLM should adhere to.

    :param field: properties field
    :param property_definition: the property definition from which to obtain the system prompt
        and allowed values

    :return (str, set): The property's system prompt and the set of allowed values if the
        property requires specific values
    """
    property_type = property_definition.get('type')
    prompt = GENERIC_PROMPT + FIELD_PROMPTS[property_type]
    if property_type == 'selection':
        selection = dict(property_definition.get('selection') or {})
        return prompt + str(selection), set(selection.keys())
    elif property_type in ('many2one', 'many2many'):
        comodel = property_definition.get('comodel')
        system_prompt = property_definition.get('system_prompt')
        if not comodel or not system_prompt:
            return prompt, set()
        return prompt, parse_ai_prompt_records(env, system_prompt, comodel)
    elif property_type == 'tags':
        tags = {name: label for name, label, color in (property_definition.get('tags') or [])}
        return prompt + str(tags), set(tags.keys())
    return prompt, False


def parse_ai_prompt_records(env, prompt, relation):
    return set(env[relation].browse({int(m.group(1)) for m in re.finditer(r'{\s*([0-9]+)\s*:.*?}', prompt)}).exists().ids)


def parse_ai_response(response, field_type, allowed_values):
    """Parse and cast a LLM response into the type expected for the given field type and checks
    that the value is in the set of allowed_values if given.

    :param response: a LLM response (string)
    :param field_type: the type of the field for which the response should be cast
    :param allowed_values: a set of values that are allowed

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
            raw_html = markdown(response, extras=['fenced-code-blocks', 'tables', 'strike'])
            return html_sanitize(raw_html or "")
        return html_sanitize(response or "")
    else:
        return response


def render_prompt(record, prompt):
    record.ensure_one()
    # usage of html_to_inner_content to remove noise (such as history steps for html fields)
    return html_to_inner_content(
        record.env['mail.render.mixin']._render_template_qweb(prompt, record._name, record._ids)[record.id]
    )

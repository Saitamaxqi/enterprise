# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime

from odoo.addons.iap.tools import iap_tools  # todo: remove when using method of ai app
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT, html_sanitize
from odoo.tools.mail import html_to_inner_content

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'  # todo: remove when using method of ai app

FIELD_PROMPTS = {
    'boolean': "Your answer must be either True or False.",
    'char': "Your answer must be a short, concise string.",
    'date': f"Your answer must follow this format: {DATE_FORMAT}.",
    'datetime': f"Your answer must follow this format: {DATETIME_FORMAT}.",
    'float': "Your answer must be a decimal number (use a dot as the decimal separator).",
    'html': "Your answer must be valid HTML (e.g., use <p>, <ul>, ...).",
    'integer': "Your answer must be a whole number.",
    'many2many': "Your answer must be a comma-separated list of integers representing record IDs. You will receive valid values in the form: {id: Description}.",
    'many2one': "Your answer must be an integer representing the selected record ID. You will receive valid values in the form: {id: Description}.",
    'monetary': "Your answer must be a float value (use a dot as the decimal separator).",
    'selection': "You must return exactly one of the keys from the dictionary provided below, which maps valid values to their display names. Return only the selected key.",
    'tags': "You must return a comma-separated list of keys from the dictionary provided below, which maps valid values to their display names. Return only the keys.",
    'text': "You can provide a longer freeform string (one or multiple sentences)."
}

GENERIC_PROMPT = """
You are a field value generator for an ERP system. When triggered, you must provide the appropriate value for a specific field.
Your answer must contain no quotes, no backticks, no explanations, no labels.
"""


# todo: remove when using method of ai app
def generate_ai_response(env, system_prompt, user_prompt):
    IrConfigSudo = env['ir.config_parameter'].sudo()
    olg_api_endpoint = IrConfigSudo.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
    database_id = IrConfigSudo.get_param('database.uuid')
    response = iap_tools.iap_jsonrpc(olg_api_endpoint + '/api/olg/1/chat', params={
        'prompt': user_prompt,
        'conversation_history': [{
            'role': 'system',
            'content': system_prompt,
        }],
        'database_id': database_id,
    }, timeout=20)
    return (response and response.get('content')) or ''


def get_ai_value(env, field_type, system_prompt, user_prompt, allowed_values):
    """Query a LLM with the given prompts and return the cast value.

    :param field_type: the field type for which the response should be cast
    :param system_prompt: the "system" prompt to pass to the LLM
    :param user_prompt: the "user" prompt to pass to the LLM
    :param allowed_values: as set containing the values that are allowed

    :return: the response of the LLM cast to the expected type if the value is allowed
    """
    return parse_ai_response(
        generate_ai_response(env, system_prompt, user_prompt),
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
    def to_int(val):
        try:
            return int(val)
        except ValueError:
            return False

    if not allowed_values:
        allowed_values = {}

    # remove the quotes the LLM can add around the text
    response = response.strip('`"\'')

    if field_type == 'boolean':
        return response.lower() == 'true'
    elif field_type in ('char', 'text'):
        return response
    elif field_type == 'integer':
        return to_int(response)
    elif field_type in ('float', 'monetary'):
        try:
            return float(response)
        except ValueError:
            return False
    elif field_type == 'datetime':
        try:
            datetime.strptime(response, DATETIME_FORMAT)
        except ValueError:
            return False
        return response
    elif field_type == 'date':
        try:
            datetime.strptime(response, DATE_FORMAT)
        except ValueError:
            return False
        return response
    elif field_type == 'selection':
        return response if response in allowed_values else False
    elif field_type == 'many2one':
        return res_id if (res_id := to_int(response)) in allowed_values else False
    elif field_type == 'many2many':
        return [
            res_id
            for value in response.split(",")
            if (res_id := to_int(value)) in allowed_values
        ]
    elif field_type == 'tags':
        return [
            stripped_value
            for value in response.split(",")
            if (stripped_value := value.strip()) in allowed_values
        ]
    elif field_type == 'html':
        return html_sanitize(response or "")
    else:
        return response


def render_prompt(record, prompt):
    record.ensure_one()
    # usage of html_to_inner_content to remove noise (such as history steps for html fields)
    return html_to_inner_content(
        record.env['mail.render.mixin']._render_template_qweb(prompt, record._name, record._ids)[record.id]
    )

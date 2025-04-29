# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import pytz
import json

from odoo import models
from odoo.exceptions import AccessError


class Model(models.AbstractModel):
    _inherit = 'base'

    def _ai_serialize_fields_data(self):
        fields_info = self.fields_get()
        result = {}

        for field_name, field_attrs in fields_info.items():
            field_type = field_attrs["type"]
            field_value = self[field_name]

            try:
                # Handle relational fields
                if field_type == "many2one":
                    result[field_name] = (
                        field_value.display_name if field_value else None
                    )
                elif field_type in ["one2many", "many2many"]:
                    linked_records = self.env[field_value._name].browse(field_value.ids)
                    if (
                        len(linked_records) > 50
                    ):  # there have been cases were too many linked records have flooded the context - avoid that by filtering them out
                        continue
                    else:
                        result[field_name] = [
                            record.display_name for record in linked_records
                        ]
                elif field_type == "binary":
                    continue  # we don't include binary fields in the record info JSON
                else:
                    # Handle basic field types (dates, etc.)
                    if isinstance(field_value, datetime.datetime):
                        user_tz = pytz.timezone(self.env.user.tz)
                        result[field_name] = (
                            field_value.astimezone(user_tz).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            if field_value
                            else None
                        )
                    elif isinstance(field_value, models.BaseModel):
                        # Handle unexpected recordset returns (shouldn't happen for non-relational fields)
                        result[field_name] = field_value.ids
                    else:
                        result[field_name] = field_value
            except AccessError:  # if the user doesn't have access to a field, don't include it in the AI's context
                continue

        return json.dumps(result, default=str)

    def _ai_initialise_context(
        self, caller_component, composer_default_prompt, text_selection=None, front_end_info=None
    ):
        context = [
            {
                "role": "system",
                "content": f"You are a helpful AI assistant to {self.env.user.display_name}. Your job is to assist with text drafting inside the ERP software Odoo.",
            }
        ]

        # If we have record info available from the front-end, pass it to the model's context
        if caller_component in ["html_field_record", "chatter_ai_button"]:
            context.append(
                {
                    "role": "system",
                    "content": f"This conversation is applying on an Odoo {self._name} record. The following JSON contains all of the records details: {front_end_info}",
                }
            )

        # If we don't have record info from the front-end and it's required, fetch the record information and pass it to the model's context
        if caller_component in ["html_field_composer", "composer_ai_button"]:
            context.append(
                {
                    "role": "system",
                    "content": f"This conversation is applying on an Odoo {self._name} record. The following JSON contains all of the records details: {self._ai_serialize_fields_data()}",
                }
            )

        # Apply the pre-prompt linked the the different ai "composers"
        context.append(
            {
                "role": "system",
                "content": composer_default_prompt,
            }
        )

        # Add some additional details for some special cases and finish the context by the "first" message sent by the assistant
        if caller_component in ["html_field_text_select"]:
            context += [
                {
                    "role": "system",
                    "content": f"The text that you will be rewritting is the following: {text_selection}",
                },
                {
                    "role": "assistant",
                    "content": self.env._("Hello, how can I rewrite your text?"),
                }
            ]
        else:
            context += [
                {
                    "role": "system",
                    "content": "ALWAYS FORMAT YOUR ANSWERS USING MARKDOWN, AVOID USING HTML. Don't use unecessary formatting like code blocks if not needed.",
                },
                {
                    "role": "assistant",
                    "content": self.env._("Hello, what can I help you with?"),
                },
            ]

        return context

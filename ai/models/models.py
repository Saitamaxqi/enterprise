# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import pytz
import json

from odoo import models
from odoo.exceptions import AccessError
from odoo.tools import OrderedSet
from odoo.tools.mail import html_to_inner_content
from odoo.tools.misc import formatLang
from odoo.tools.mimetypes import guess_mimetype

AI_SUPPORTED_IMG_TYPES = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


class Model(models.AbstractModel):
    _inherit = 'base'

    def _ai_truncate(self, value, size=60):
        # Limit the size of the field we can, to try to limit prompt injection...
        if not isinstance(value, str) or len(value) < size:
            return value
        return value[:max(0, size - 3)] + "..."

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

    ################
    #  Extensions  #
    ################

    def _ai_format(self, files_dict):
        # meant to be overridden by models for which one wants to send more than just the
        # display name or filter records to send (see mail.message for an example)
        # todo: add a limit?
        return self._ai_read(['display_name'], files_dict)

    def _ai_read(self, fnames, files_dict):
        if not fnames:
            return self._ai_format(files_dict)
        vals_list = self.read(fnames, load=None)
        for fname in fnames:
            field = self._fields.get(fname)
            if field.type in ('binary', 'image'):
                if field.attachment and (len(self) > 1 or self._origin.id):  # attachment is not created yet in quick creation
                    attachments = self.env['ir.attachment'].search([
                        ('res_model', '=', self._name),
                        ('res_field', '=', fname),
                        ('res_id', 'in', self.ids)  # ._origin?
                    ])
                    attachments._ai_format(files_dict)  # populate the files_dict
                    attachments_by_resid = {att.res_id: att for att in attachments}
                    for vals in vals_list:
                        if not vals[fname] or (res_id := vals['id'] or vals['id'].origin) not in attachments_by_resid:
                            continue
                        vals[fname] = files_dict[attachments_by_resid[res_id].checksum]['file_ref']
                else:
                    for vals in vals_list:
                        checksum = self.env['ir.attachment']._compute_checksum(vals[fname])
                        if checksum not in files_dict:
                            raw = base64.b64decode(vals[fname])
                            mimetype = guess_mimetype(raw)
                            extension = mimetype.split("/")[-1]
                            file_ref = f'<file_#{len(files_dict) + 1}>'
                            if is_uri := extension in (*AI_SUPPORTED_IMG_TYPES, 'pdf'):
                                value = f'data:{mimetype};base64,{vals[fname].decode()}'
                            else:
                                try:
                                    value = self.env['ir.attachment']._index(vals[fname], mimetype, checksum=checksum)
                                except TypeError:
                                    value = self.env['ir.attachment']._index(vals[fname], mimetype)
                            files_dict[checksum] = {
                                'type': 'pdf' if extension == 'pdf' else 'image' if is_uri else 'text',
                                'value': value,
                                'file_ref': file_ref,
                            }
                        vals[fname] = files_dict[checksum]['file_ref']
            elif field.type in ('date', 'datetime'):
                for vals in vals_list:
                    vals[fname] = field.to_string(vals[fname])
            elif field.type == 'html':
                for vals in vals_list:
                    vals[fname] = html_to_inner_content(vals[fname])
            elif field.type in ('many2many', 'many2one', 'one2many'):
                for vals in vals_list:
                    vals[fname] = {'model': field.comodel_name, 'ids': vals[fname]}
            elif field.type in ('many2one_reference', 'reference'):
                vals_by_ids = {vals['id']: vals for vals in vals_list}
                for record in self:
                    record_vals = vals_by_ids[record.id]
                    if not record[fname]:
                        record_vals[fname] = False  # keep falsy values consistent for the LLM
                    if field.type == 'many2one_reference':
                        record_vals[fname] = {'model': model, 'ids': record_vals[fname]} if (model := record[field.model_field]) else False
                    else:
                        record_vals[fname] = {'model': record._name, 'ids': record.id}
            elif field.type == 'monetary':
                currency_field = field.get_currency_field(self)
                if currency_field:
                    currency = self[currency_field]
                    for vals in vals_list:
                        vals[fname] = formatLang(self.env, vals[fname], currency_obj=currency)

        for vals in vals_list:
            if not vals['id']:
                vals['id'] = self._origin.id
        return vals_list

    def _get_ai_context(self, field_paths):
        """ Get the context dict for a record given a list of field paths.
        The context dict is a mini-orm snapshot with values formatted for LLM usage.
        It is a dictionary of the form:

        .. code-block:: python

            {
                "model_A": [
                    {
                        "id": 1,
                        "field_A": "val_1",
                        "field_B": {"model": "model_B", "ids": [3]},
                    },
                    {
                        "id": 2,
                        "field_A": "val_2",
                        "field_B": {"model": "model_B", "ids": [4]},
                    }
                ],
                "model_B": [
                    {
                        "id": 3,
                        "field_C": "val_3"
                    },
                    {
                        "id": 4,
                        "field_C": "val_4"
                    }
                ]
            }
        """
        self.ensure_one()
        models = {}

        def _map_to_models(records, path):
            model = records._name
            ids = OrderedSet(records.ids)
            if model not in models:
                models[model] = {'fields': OrderedSet(), 'ids': ids}
            else:
                models[model]['ids'] |= ids
            if not path:
                return
            fname = path[0]
            field = records._fields.get(fname)
            if not field:
                return
            if field.type in ('many2many', 'many2one', 'one2many'):
                _map_to_models(records[fname], path[1:])
            elif field.type == 'reference':
                for record in records:
                    if record[fname]:
                        _map_to_models(record[fname], path[1:])
            elif field.type == 'many2one_reference':
                for record in records:
                    if (ref_model := record[field.model_field]) and (ref_id := record[fname]):
                        _map_to_models(self.env[ref_model].browse(ref_id), path[1:])
            models[model]['fields'].add(fname)

        # get a mapping {model: {fields, ids}} to know which fields to read on which records
        for path in field_paths:
            _map_to_models(self, path.split("."))

        snapshot = {}
        files_dict = {}  # files are sent separately to LLMs
        for model, info in models.items():
            records = self.env[model].browse(info['ids'])
            if model == self._name and not self.id:
                records = records.filtered(lambda r: r.id != self._origin.id) | self  # unsaved changes
            snapshot[model] = records._ai_read(info['fields'], files_dict)

        return snapshot, list(files_dict.values())

    def _ai_format_records(self):
        """Format what will be in the prompt when we inserted records.

        It needs to return a dict which keys are the records ids, and
        the value of the dict can be anything.
        """
        return {record.id: record.display_name for record in self}

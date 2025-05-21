# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import collections
import logging

from odoo import _, api, Command, models
from odoo.addons.ai_fields.tools import get_ai_value, get_field_prompt_vals, get_property_prompt_vals, parse_ai_prompt_values
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools import html_sanitize, OrderedSet
from odoo.tools.mail import html_to_inner_content
from odoo.tools.misc import formatLang
from odoo.tools.mimetypes import guess_mimetype

AI_SUPPORTED_IMG_TYPES = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    ###############
    #  Overrides  #
    ###############

    @api.model
    def _create(self, data_list):
        """When a record of a model with an ai field or property is created, trigger the cron to
        fill the ai fields/properties.
        """
        trigger_cron = False
        for field in self._fields.values():
            if field.type == 'properties':
                values = [d['stored'].get(field.name) for d in data_list]
                if any(p.get('ai') and p.get('system_prompt') for value in values for p in (value or [])):
                    trigger_cron = True
                    break
            elif field.type in ('char', 'text', 'html') and hasattr(field, 'ai') and field.ai:
                trigger_cron = True
                break

        if trigger_cron and (ai_fields_cron := self.env.ref('ai_fields.ir_cron_fill_ai_fields', raise_if_not_found=False)):
            ai_fields_cron._trigger()

        return super()._create(data_list)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if attributes is None or 'ai' in attributes:
            for fname, val in res.items():
                val['ai'] = hasattr(self._fields[fname], 'ai') and self._fields[fname].ai
        return res

    def write(self, vals):
        """When a property definition is modified or when the definition record is updated, trigger
        the cron to fill the ai properties.
        """
        res = super().write(vals)
        if not self:
            return res

        trigger_cron = False
        for field in self._fields.values():
            if field.type == 'properties':
                def_rec_name = self._fields[field.definition_record].name
                if vals.get(def_rec_name):
                    if any(p.get('ai') and p.get('system_prompt') for p in (self[0][def_rec_name][field.definition_record_field] or [])):
                        trigger_cron = True
                        break
            elif field.type == 'properties_definition':
                if any(p.get('ai') and p.get('system_prompt') for p in (vals.get(field.name) or [])):
                    trigger_cron = True
                    break

        if trigger_cron and (ai_fields_cron := self.env.ref('ai_fields.ir_cron_fill_ai_fields', raise_if_not_found=False)):
            ai_fields_cron._trigger()
        return res

    def _additional_allowed_keys_properties_definition(self):
        return super()._additional_allowed_keys_properties_definition() + ('ai', 'system_prompt', 'ai_domain')

    def _html_sanitize_prompt_properties_definition(self, properties_definition):
        if not properties_definition:
            return properties_definition

        for property_definition in properties_definition:
            if property_definition.get('system_prompt'):
                # Equivalent of `sanitize='email_outgoing'` on mail template body
                property_definition['system_prompt'] = html_sanitize(
                    property_definition['system_prompt'],
                    sanitize_tags=True,
                    sanitize_attributes=True,
                    sanitize_style=True,
                    strip_style=True,
                    output_method='xml',
                )
        return properties_definition

    @api.model
    def _get_view_field_attributes(self):
        attrs = super()._get_view_field_attributes()
        attrs.append('ai')
        return attrs

    def _valid_field_parameter(self, field, name):
        return name == 'ai' or super()._valid_field_parameter(field, name)

    def _validate_properties_definition(self, properties_definition, field):
        super()._validate_properties_definition(properties_definition, field)

        self._html_sanitize_prompt_properties_definition(properties_definition)

        if self.env.su or self.env.user.has_group('mail.group_mail_template_editor'):
            return

        for property_definition in properties_definition:
            if prompt := property_definition.get('system_prompt'):
                model_names = [properties_field.model_name for properties_field in field.properties_fields]
                __, expressions, record_ids = parse_ai_prompt_values(self.env, prompt, property_definition.get('comodel'), False)
                for model_name in model_names:
                    allowed_expressions = self.env[model_name].mail_allowed_qweb_expressions()
                    for expression in expressions:
                        if f"object.{expression}" not in allowed_expressions:
                            raise AccessError(_("You can not use the field %(field)s in a prompt."))
                if (comodel := property_definition.get('comodel')) and record_ids:
                    self.env[comodel].browse(record_ids).check_access("read")

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
                                    value = self._index(vals[fname], mimetype, checksum=checksum)
                                except TypeError:
                                    value = self._index(vals[fname], mimetype)
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

    def _fill_ai_field(self, field, field_prompt=None):
        """Assign a value to the specified field in the given records based on the response of a
        LLM. If no prompt is provided and the field is an AI field, it uses the field's prompt.

        :param field: the field object for which the values should be obtained
        :param field_prompt: the prompt to use for generating the values. If not provided and
          the field is an AI field, the field's default prompt is used.

        :return None
        """
        if field_prompt is None and not (hasattr(field, 'ai') and field.ai):
            raise ValueError(f"The field {field.name} has no AI prompt")
        user_prompt, context_fields, allowed_values = get_field_prompt_vals(self.env, field, field_prompt)
        for record in self:
            try:
                record[field.name] = get_ai_value(record, field.type, user_prompt, context_fields, allowed_values)
            except Exception as e:  # noqa: BLE001
                _logger.info("Could not get a value for an AI Field (%s on %s): %s", field.name, field.model_name, e)
                record[field.name] = ""  # prevent query llm again for the field (unresolvable/timeout)

    def _fill_ai_property(self, fname, property_definition):
        """Assign values to the specified AI property field for the records in `self` using LLM.
        The records must share the same property definition.

        :param fname: the name of the properties field
        :param property_definition: the definition of the property

        :return: None
        """
        if not property_definition.get('system_prompt'):
            raise ValueError(f"The property {property_definition['string']} has no AI prompt")
        user_prompt, context_fields, allowed_values = get_property_prompt_vals(self.env, property_definition)
        properties = {v['id']: v[fname] for v in self.read([fname])}
        for record in self:
            try:
                value = get_ai_value(record, property_definition.get('type'), user_prompt, context_fields, allowed_values)
            except Exception as e:  # noqa: BLE001
                _logger.info("Could not get a value for an AI property (%s in %s on %s): %s", property_definition['name'], fname, self._name, e)
                value = False  # prevent query llm again for the property (unresolvable/timeout)

            # update the property value (without overriding existing properties)
            # we don't write the definition otherwise we will retrigger the cron if there
            # is a property that has not been processed yet
            record[fname] = {
                p['name']: value if p['name'] == property_definition['name'] else p.get('value')
                for p in properties.get(record.id, [])
                if p['name'] == property_definition['name'] or 'value' in p
            }

    def get_ai_field_value(self, fname, changes):
        """Get the value of an AI field based on the response of a LLM.

        :param fname: name of the field for which the value should be obtained
        :param changes: dict of field values containing the changes to apply before querying
            the LLM

        :return: the value to apply to the field in the format of :meth:`web_read`, except for
            many2many fields where the value is a command to apply
        """
        self.check_access("read")
        self.check_access("write")
        record = self.new(changes, origin=self)
        field = self._fields.get(fname)
        if not field:
            raise ValueError(f"The field {fname} is not defined on {self._name}")
        if not (hasattr(field, 'ai') and field.ai):
            raise ValueError(f"The field {fname} has no AI prompt")
        user_prompt, context_fields, allowed_values = get_field_prompt_vals(self.env, field)
        if field.type in ('many2many', 'many2one') and not allowed_values:
            # add most frequent records if no record in prompt
            records = self.ai_find_default_records(field.comodel_name, field.domain, fname)
            allowed_values = {r.id: r.display_name for r in records}
        val = get_ai_value(record, field.type, user_prompt, context_fields, allowed_values)  # currency?
        if field.type == 'many2one':
            return bool(val) and self.env[field.comodel_name].browse(val).read(['id', 'display_name'])[0]
        elif field.type == 'many2many':
            return [[Command.SET, 0, val or []]]
        return val

    def get_ai_property_value(self, full_name, changes):
        """Get the value of an AI property based on the response of a LLM.

        :param full_name: full name of the property (field.property) for which the value should be
            obtained
        :param changes: dict of field values containing the changes to apply before querying the
            LLM

        :return: The value to apply to the property field in the format of :meth:`web_read`
        """
        self.check_access("read")
        self.check_access("write")
        record = self.new(changes, origin=self)
        property_definition = None
        fname, pname = full_name.split(".")

        if changes:
            # use the updated property definition if it changed
            properties_definition = changes.get(fname)

            if properties_definition:
                def_field = self[self._fields[fname].definition_record]._fields[self._fields[fname].definition_record_field]
                properties_definition = [p for p in properties_definition if not p.get('definition_deleted')]
                property_definition = next((p for p in properties_definition if p['name'] == pname), None)
                for p in properties_definition:
                    p.pop('value', None)
                    p.pop('definition_changed', None)
                def_field._validate_properties_definition(properties_definition, self.env)

        if property_definition is None:
            property_definition = self.get_property_definition(full_name)
        if not (property_definition.get('ai') and property_definition.get('system_prompt')):
            raise ValueError(f"The property {full_name} has no system prompt")
        property_type = property_definition['type']
        if property_type in ('many2many', 'many2one'):
            if not property_definition.get('comodel'):
                return property_type == 'many2many' and []
        user_prompt, context_fields, allowed_values = get_property_prompt_vals(self.env, property_definition)
        if property_type in ('many2many', 'many2one') and not allowed_values and property_definition.get('comodel'):
            # add most frequent records if no record in prompt
            records = self.ai_find_default_records(property_definition.get('comodel'), property_definition.get('domain'), fname, pname)
            allowed_values = {r.id: r.display_name for r in records}
        val = get_ai_value(record, property_type, user_prompt, context_fields, allowed_values)
        if property_type == 'many2one':
            return bool(val) and self.env[property_definition['comodel']].browse(val).read(['id', 'display_name'])[0]
        if property_type == 'many2many':
            records = self.env[property_definition['comodel']].browse(val)
            return [[rec['id'], rec['display_name']] for rec in records.read(['id', 'display_name'])] if records else []
        return val

    @api.model
    def ai_find_default_records(self, comodel, domain, field_name, property_name=None):
        """Heuristic for relational AI fields / properties, find the most used records, and fill if necessary.

        Note that `field_name` can be empty, when creating new field in studio.
        """
        limit = int(self.env['ir.config_parameter'].sudo().get_param('ai_field.insert_x_first_records', '200'))
        domain = ast.literal_eval(domain or "[]") if isinstance(domain, str) else (domain or [])

        if field_name and not self._fields[field_name].store:
            return []

        records_ids = []
        if not property_name and field_name:
            records_ids = [
                record_id
                for r in self.search([(field_name, 'any', domain)], limit=limit * 5, order="id DESC")
                for record_id in r[field_name].ids
            ]
        elif property_name:
            # `any` operator not working on relational properties (because too costly to do)
            definition = self.get_property_definition(f"{field_name}.{property_name}")
            if definition:
                values = self.search_read([(f"{field_name}.{property_name}", '!=', False)], [field_name], limit=limit * 5, order="id DESC")
                values = [next(p.get('value') for p in v[field_name] if p.get('name') == property_name) for v in values]
                if definition.get('type') == 'many2one':
                    records_ids = [v[0] for v in values if v]
                elif definition.get('type') == 'many2many':
                    records_ids = [v[0] for rec in values for v in rec if rec and v]
                allowed_ids = self.env[comodel].browse(records_ids).filtered_domain(domain).ids
                records_ids = [i for i in records_ids if i in allowed_ids]

        records_ids = [c[0] for c in collections.Counter(records_ids).most_common(limit)]
        records = self.env[comodel].browse(records_ids)

        if len(records) < limit:  # If we didn't reach the limit, fill with other records
            records |= self.env[comodel].search(
                Domain.AND([domain, [('id', 'not in', records.ids)]]),
                limit=limit - len(records),
                order="id DESC",
            )

        return records

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import json
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.iap.tools import iap_tools
from odoo.tests import TransactionCase, tagged
from odoo.tools import SQL


@tagged('post_install', '-at_install')
class TestAiFieldsCrons(TransactionCase, CronMixinCase):
    def test_ai_fields_cron_trigger(self):
        ai_field_cron_id = self.env.ref('ai_fields.ir_cron_fill_ai_fields').id
        # cron not triggered when creating a record on a model without ai field
        with self.capture_triggers(ai_field_cron_id) as capt:
            self.env["test.ai.fields.no.ai"].create({"name": "Record"})
            self.assertFalse(len(capt.records))

        values = {
            "name": "x_ai_char",
            "model_id": self.env["ir.model"]._get("test.ai.fields.no.ai").id,
            "ttype": "char",
        }
        values_ai = {
            "ai": True,
            "system_prompt": "System Prompt {{object.name}}",
        }

        # cron triggered when creating an ai field
        with self.capture_triggers(ai_field_cron_id) as capt:
            self.env["ir.model.fields"].create(values | values_ai)
            self.assertTrue(len(capt.records))

        # cron not triggered when creating a non ai field, but triggered when making it an ai field
        with self.capture_triggers(ai_field_cron_id) as capt:
            field = self.env["ir.model.fields"].create(values | {"name": "x_ai_char_2"})
            self.assertFalse(len(capt.records))
            field.write(values_ai)
            self.assertTrue(len(capt.records))

        # cron triggered when creating a record on a model with an ai field
        with self.capture_triggers(ai_field_cron_id) as capt:
            self.env["test.ai.fields.no.ai"].create({"name": "Record"})
            self.assertTrue(len(capt.records))

    def test_ai_properties_cron_trigger(self):
        ai_properties_cron = self.env.ref('ai_fields.ir_cron_fill_ai_fields').id
        definition_no_ai = self.env["test.ai.fields.parent"].create({"properties_definition": []})
        definition_with_ai = self.env["test.ai.fields.parent"].create({"properties_definition": [
            {"name": "ai_property", "type": "char", "ai": True, "system_prompt": "AI Prompt"}
        ]})

        # cron not triggered when creating a record with a property definition without an ai property
        with self.capture_triggers(ai_properties_cron) as capt:
            self.env["test.ai.fields.model"].create({"parent_id": definition_no_ai.id})
            self.assertFalse(len(capt.records))

        # cron triggered when adding an AI property to an existing definition
        with self.capture_triggers(ai_properties_cron) as capt:
            definition_no_ai.write({"properties_definition": [
                {"name": "new_ai_property", "type": "char", "ai": True, "system_prompt": "Another AI Prompt"}
            ]})
            self.assertTrue(len(capt.records))

        definition_no_ai.properties_definition = []
        # cron not triggered if changing the definition record to a definition without an ai property
        record = self.env["test.ai.fields.model"].create({"parent_id": definition_with_ai.id})
        with self.capture_triggers(ai_properties_cron) as capt:
            record.write({"parent_id": definition_no_ai.id})
            record.flush_recordset()  # triggers the write on properties
            self.assertFalse(len(capt.records))

        # cron triggered if changing the definition record to a definition with an ai property
        record = self.env["test.ai.fields.model"].create({"parent_id": definition_no_ai.id})
        with self.capture_triggers(ai_properties_cron) as capt:
            record.parent_id = definition_with_ai
            self.assertTrue(len(capt.records))

        # cron triggered if creating a record with a definition that has an ai property
        with self.capture_triggers(ai_properties_cron) as capt:
            self.env["test.ai.fields.model"].create({'parent_id': definition_with_ai.id})
            self.assertTrue(len(capt.records))


@tagged('post_install', '-at_install')
class TestAiFields(TransactionCase):
    def test_ai_field_cron_fields(self):
        """Check that the cron only process NULL textual fields (that are in the ai_domain)."""
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": f"response value {params.get('prompt')}"}

        model = self.env["test.ai.fields.model"]

        # create ai fields of different types
        field_definitions = [
            {"name": "x_ai_char", "ttype": "char", "ai": True, "system_prompt": "char prompt"},
            {"name": "x_ai_text", "ttype": "text", "ai": True, "system_prompt": "text prompt"},
            {"name": "x_ai_html", "ttype": "html", "ai": True, "system_prompt": "html prompt"},
            {"name": "x_ai_integer", "ttype": "integer", "ai": True, "system_prompt": "int prompt"},
            {"name": "x_ai_boolean", "ttype": "boolean", "ai": True, "system_prompt": "bool prompt"},
        ]

        ai_fields = {f["name"]: self.env["ir.model.fields"].create(f | {"model_id": self.env["ir.model"]._get("test.ai.fields.model").id}) for f in field_definitions}

        # create records with different AI field values
        records = model.create([
            {"x_ai_char": None, "x_ai_text": None, "x_ai_html": None, "x_ai_integer": 0, "x_ai_boolean": False},
            {"x_ai_char": "", "x_ai_text": "", "x_ai_html": "", "x_ai_integer": 0, "x_ai_boolean": False},
            {"x_ai_char": "existing", "x_ai_text": "existing", "x_ai_html": "<p>existing</p>", "x_ai_integer": 5, "x_ai_boolean": True},
        ])

        # update ai_domain to exclude record[0]
        ai_fields["x_ai_char"].write({"ai_domain": [["id", "!=", records[0].id]]})

        # sanity check, ensure values are correct in database
        self.env.flush_all()
        self.env.cr.execute(SQL("SELECT id, x_ai_char, x_ai_text, x_ai_html, x_ai_integer, x_ai_boolean FROM test_ai_fields_model WHERE id = ANY(%s)", records.ids))
        result = {row[0]: row[1:] for row in self.env.cr.fetchall()}

        self.assertEqual(result[records[0].id], (None, None, None, 0, False))
        self.assertEqual(result[records[1].id], ("", "", "", 0, False))
        self.assertEqual(result[records[2].id], ("existing", "existing", "<p>existing</p>", 5, True))

        # run the cron job
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc), self.enter_registry_test_mode():
            self.env.ref('ai_fields.ir_cron_fill_ai_fields').method_direct_trigger()

        self.env.flush_all()
        self.env.cr.execute(SQL("SELECT id, x_ai_char, x_ai_text, x_ai_html, x_ai_integer, x_ai_boolean FROM test_ai_fields_model WHERE id = ANY(%s)", records.ids))
        result = {row[0]: row[1:] for row in self.env.cr.fetchall()}

        self.assertEqual(
            result[records[0].id],
            (None, "response value text prompt", "<p>response value html prompt</p>", 0, False),
            "Textual fields should have been updated (except char which is excluded by ai_domain)"
        )
        # only NULL textual fields should be updated
        self.assertEqual(result[records[1].id], ("", "", "", 0, False), "No field should have been updated")
        self.assertEqual(result[records[2].id], ("existing", "existing", "<p>existing</p>", 5, True), "No field should have been updated")

    def test_ai_field_cron_properties(self):

        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": f"response value {params.get('prompt')}"}

        parent = self.env["test.ai.fields.parent"].create({})

        # Record created before the definition has been created
        record_0 = self.env["test.ai.fields.model"].create({})
        record_1 = self.env["test.ai.fields.model"].create({"parent_id": parent.id})

        parent.write({"properties_definition": [{"type": "char", "name": "char", "ai": True, "system_prompt": 'id=<t t-out="object.id">id</t>'}]})

        records = record_2, record_3, record_4, record_5 = self.env["test.ai.fields.model"].create([
            {"parent_id": parent.id, "properties": [{"type": "char", "name": "char"}]},
            {"parent_id": parent.id, "properties": [{"type": "char", "name": "char", "value": ""}]},
            {"parent_id": parent.id, "properties": [{"type": "char", "name": "char", "value": False}]},
            {"parent_id": parent.id, "properties": [{"type": "char", "name": "char"}]},

        ])
        records |= record_0 | record_1

        # Change the `ai_domain`
        parent.write({"properties_definition": [{"type": "char", "name": "char", "ai": True, "system_prompt": 'id=<t t-out="object.id">id</t>', "ai_domain": [["id", "!=", record_2.id]]}]})

        # Sanity check, ensure the values are correct in database
        self.env.cr.execute(SQL("SELECT id, properties FROM test_ai_fields_model WHERE id = ANY(%s)", records.ids))
        result = dict(self.env.cr.fetchall())
        self.assertEqual(result.get(record_0.id), None)
        self.assertEqual(result.get(record_1.id), None)
        self.assertEqual(result.get(record_2.id), {})
        self.assertEqual(result.get(record_3.id), {"char": False})
        self.assertEqual(result.get(record_4.id), {"char": False})
        self.assertEqual(result.get(record_5.id), {})

        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc), self.enter_registry_test_mode():
            self.env.ref('ai_fields.ir_cron_fill_ai_fields').method_direct_trigger()
        self.env.flush_all()

        self.env.cr.execute(SQL("SELECT id, properties FROM test_ai_fields_model WHERE id = ANY(%s)", records.ids))
        result = dict(self.env.cr.fetchall())
        self.assertEqual(result.get(record_0.id), None)
        self.assertEqual(result.get(record_1.id), {"char": f"response value id={record_1.id}"})
        self.assertEqual(result.get(record_2.id), {}, "The AI domain should have prevented the update of that record")
        self.assertEqual(result.get(record_3.id), {"char": False})
        self.assertEqual(result.get(record_4.id), {"char": False})
        self.assertEqual(result.get(record_5.id), {"char": f"response value id={record_5.id}"})

    def test_ai_read(self):
        record = self.env['res.partner'].create({
            'name': 'Name',
            'bank_ids': [
                Command.create({'acc_number': f'bank_{i}', 'note': f'note {i}'})
                for i in range(3)
            ],
        })
        result = record._ai_read("name", "bank_ids.acc_number", "bank_ids.note")
        self.assertEqual(result, json.dumps([{'id': record.id, 'name': 'Name', 'bank_ids': [
            {'id': record.bank_ids[0].id, 'acc_number': 'bank_0', 'note': 'note 0'},
            {'id': record.bank_ids[1].id, 'acc_number': 'bank_1', 'note': 'note 1'},
            {'id': record.bank_ids[2].id, 'acc_number': 'bank_2', 'note': 'note 2'},
        ]}]))

        # Check that the datetime object are stringified in the JSON
        result = record._ai_read("create_date", "write_date")
        self.assertEqual(result, json.dumps([{
            'id': record.id,
            'create_date': fields.Datetime.to_string(record.create_date),
            'write_date': fields.Datetime.to_string(record.write_date),
        }]))

    def test_ai_field_sanitize(self):
        system_prompt = '<t t-out="object.name"/> <img src="x" onerror="alert(1)"/>'
        expected = '<span><t t-out="object.name"/> <img src="x"/></span>'
        properties_definition = [{
            "type": "char",
            "name": "char",
            "ai": True,
            "system_prompt": system_prompt,
        }]
        parent = self.env["test.ai.fields.parent"].create({"properties_definition": copy.deepcopy(properties_definition)})

        self.assertEqual(parent.properties_definition[0]['system_prompt'], expected)
        record = self.env["test.ai.fields.model"].create({"parent_id": parent.id})
        self.assertEqual(record.read(["properties"])[0]["properties"][0]["system_prompt"], expected)

        # Check that value in database is sanitized
        self.env.cr.execute("SELECT properties_definition[0]->'system_prompt' FROM test_ai_fields_parent WHERE id = %s", [parent.id])
        property_prompt = self.env.cr.fetchone()[0]
        self.assertEqual(property_prompt, expected)

        self.assertIn("onerror", str(properties_definition))
        self.env.cr.execute(
            "UPDATE test_ai_fields_parent SET properties_definition = %s WHERE id = %s",
            [json.dumps(properties_definition), parent.id],
        )
        self.env.flush_all()

        self.assertEqual(parent.read(["properties_definition"])[0]["properties_definition"][0]["system_prompt"], expected)
        self.assertEqual(record.read(["properties"])[0]["properties"][0]["system_prompt"], expected)

        field = self.env['ir.model.fields'].create({
            "name": "x_ai_char",
            "model_id": self.env["ir.model"]._get("test.ai.fields.no.ai").id,
            "ttype": "char",
            'ai': True,
            'system_prompt': system_prompt,
        })
        self.assertEqual(field.system_prompt, expected)

        # Test that the HTML generated by the LLM is sanitized
        self.env['ir.model.fields'].create({
            "name": "x_ai_html",
            "model_id": self.env["ir.model"]._get("test.ai.fields.model").id,
            "ttype": "html",
            'ai': True,
            'system_prompt': 'prompt',
        })

        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": '<img src="x" onerror="alert(1)"/>'}

        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc), self.enter_registry_test_mode():
            value = record.get_ai_field_value("x_ai_html", None)
            self.assertEqual(value, '<img src="x">')

        record.write({
            "properties": [{
                "type": "html",
                "name": "test_html",
                "ai": True,
                "system_prompt": "system_prompt",
                "definition_changed": True,
            }],
        })
        record.flush_recordset()
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc), self.enter_registry_test_mode():
            value = record.get_ai_property_value("properties.test_html", None)
        self.assertEqual(value, '<img src="x">')

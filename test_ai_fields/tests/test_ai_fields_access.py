# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAiFieldsAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin, cls.internal = cls.env['res.users'].create([
            {
                'email': "admin_ai@example.com",
                'group_ids': [Command.link(cls.env.ref('base.group_user').id), Command.link(cls.env.ref('mail.group_mail_template_editor').id)],
                'login': "admin_ai",
                'name': "admin_ai",
            },
            {
                'login': 'internal_ai',
                'group_ids': [Command.link(cls.env.ref('base.group_user').id)],
                'name': 'internal_ai',
            },
        ])
        cls.parent = cls.env["test.ai.fields.parent"].create(
            {"properties_definition": [{"type": "char", "name": "char"}]})
        cls.record = cls.env["test.ai.fields.model"].create({"parent_id": cls.parent.id})

    def test_ai_field_access_properties(self):
        """Test that only the template editor can write complex expressions."""
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": "1337"}

        self.record.with_user(self.internal).write({"properties": [{"type": "char", "name": "char", "definition_changed": True, "ai": True, "system_prompt": "This is my prompt <t t-out='object.test_ai_fields'/>"}]})
        self.env.flush_all()

        with patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval, \
            patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            values = self.record.get_ai_property_value("properties.char", None)
            self.assertEqual(values, "1337")
            self.assertFalse(unsafe_eval.called, "Should not evaluate the code a normal user wrote")

        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            value = {"properties": [{"type": "char", "name": "char", "ai": True, "system_prompt": "This is my prompt}}", "value": "value"}]}
            self.assertEqual(self.record.with_user(self.internal).get_ai_property_value("properties.char", value), "1337")

        with patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval, \
             patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc), \
            self.assertRaises(AccessError):
            values = {"properties": [{"type": "char", "name": "char", "ai": True, "system_prompt": "This is my prompt <t t-out='1+1'/>}}", "value": "value"}]}
            value = self.record.with_user(self.internal).get_ai_property_value("properties.char", values)
            self.assertEqual(value, "1337")
            self.assertFalse(unsafe_eval.called, "Should not evaluate the code a normal user wrote")

        with self.assertRaises(AccessError):
            self.record.with_user(self.internal).write({"properties": [{"type": "char", "name": "char", "definition_changed": True, "ai": True, "system_prompt": "Bad prompt <t t-out='1+1'/>"}]})
        self.record.with_user(self.admin).write({"properties": [{"type": "char", "name": "char", "definition_changed": True, "ai": True, "system_prompt": "Bad prompt <t t-out='1+1'/>"}]})

        with self.assertRaises(AccessError):
            self.parent.with_user(self.internal).write({"properties_definition": [{"type": "char", "name": "char", "ai": True, "system_prompt": "Bad prompt <t t-out='1+1'/>"}]})

        with self.assertRaises(AccessError):
            # Try to write forbidden expression on ai = False properties
            self.parent.with_user(self.internal).write({"properties_definition": [{"type": "char", "name": "char", "ai": False, "system_prompt": "Bad prompt <t t-out='1+1'/>"}]})

        with self.assertRaises(AccessError):
            self.env["test.ai.fields.parent"].with_user(self.internal).create(
                {"properties_definition": [{"type": "char", "name": "char", "ai": True, "system_prompt": "Bad prompt <t t-out='1+1'/>"}]})
        self.env["test.ai.fields.parent"].with_user(self.admin).create(
            {"properties_definition": [{"type": "char", "name": "char", "ai": True, "system_prompt": "Bad prompt <t t-out='1+1'/>"}]})

        # Should allow `test_ai_fields` because it's whitelisted on the child model
        self.env["test.ai.fields.definition"].with_user(self.internal).create(
            {"properties_definition": [{"type": "char", "name": "char", "ai": True, "system_prompt": "Bad prompt <t t-out='object.test_ai_fields'/>}}"}]})

        # Try to inject Qweb in selection options (they are added in the prompt)
        def _mocked_iap_jsonrpc_selection(url, params, **kwargs):
            self.assertNotIn("1337", str(params))
            return {"content": ""}

        self.record.parent_id.write({
            "properties_definition": [{
                "type": "selection",
                "name": "selection",
                "selection": [["<t t-out='1+1336'/>", '<t t-out="1+1336"/>']],
                "ai": True,
                "system_prompt": "Good prompt",
            }],
        })
        self.env.flush_all()

        with patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval, \
             patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc_selection):
            self.record.get_ai_property_value('properties.selection', None)
            self.record._fill_ai_property('properties', self.record.parent_id.properties_definition[0])
            self.assertFalse(unsafe_eval.called)

    def test_ai_field_access_fields(self):
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": f"response: {params.get('prompt')}"}

        self.env["ir.model.fields"].create({
            "name": "x_ai_char",
            "model_id": self.env["ir.model"]._get("test.ai.fields.model").id,
            "ttype": "char",
            "ai": True,
            "system_prompt": "System Prompt <t t-out='object.name'/>",
        })

        self.record.name = "Test"
        with patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval, \
            patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            value = self.record.get_ai_field_value("x_ai_char", None)
            self.assertFalse(unsafe_eval.called, "Should not evaluate the code a normal user wrote")
            self.assertEqual(value, "response: System Prompt Test")

    def test_ai_fields_validation_many2one(self):
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": str(response)}

        records = self.env['res.partner'].create([{'name': f'partner {i}'} for i in range(4)])

        # Simulate that we removed the record we inserted in the prompt
        id_removed = self.env['res.partner'].search([], order="id DESC", limit=1).id + 1
        description = ["{%s: Description}" % r for r in (*records.ids[:3], id_removed)]

        system_prompt = 'This is my prompt 99 <t t-out="object.name"/>}}. Choose between: ' + ' or '.join(description)

        self.record.write({"properties": [{
            "type": "many2one",
            "name": "many2one",
            "comodel": "res.partner",
            "definition_changed": True,
            "ai": True,
            "system_prompt": system_prompt,
        }]})
        self.env.flush_all()

        # Ensure that we don't parse the rendered prompt
        self.record.name = "{%s: Description}" % records[3].id

        response = records[0].id
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertEqual(self.record.get_ai_property_value("properties.many2one", None), {'id': records[0].id, 'display_name': records[0].display_name})

        # The record doesn't exist but is in the prompt
        response = id_removed
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertFalse(self.record.get_ai_property_value("properties.many2one", None))

        # The record exists but is not in the prompt
        response = records[3].id
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertFalse(self.record.get_ai_property_value("properties.many2one", None))

        # Test missing model
        self.record.write({"properties": [{
            "type": "many2one",
            "name": "many2one",
            # comodel is missing
            "definition_changed": True,
            "ai": True,
            "system_prompt": system_prompt,
        }]})
        self.env.flush_all()
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertFalse(self.record.get_ai_property_value("properties.many2one", None))

    def test_ai_fields_validation_many2many(self):
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": response}

        records = self.env['res.partner'].create([{'name': f'partner {i}'} for i in range(5)])

        # Ensure that we don't parse the rendered prompt
        self.record.name = "{%s: Description}" % records[3].id

        # Simulate that we removed the record we inserted in the prompt
        id_removed = self.env['res.partner'].search([], order="id DESC", limit=1).id + 1
        description = ["{%s: Description}" % r for r in (*records.ids[:4], id_removed)]

        system_prompt = 'This is my prompt 99 <t t-out="object.name"/>}}. Choose between: ' + ' or '.join(description)

        self.record.write({"properties": [{
            "type": "many2many",
            "name": "many2many",
            "comodel": "res.partner",
            "definition_changed": True,
            "ai": True,
            "system_prompt": system_prompt,
        }]})
        self.env.flush_all()

        # Ensure that we don't parse the rendered prompt
        self.record.name = "{%s: Description}" % records[4].id

        response = f"{records[0].id}, {id_removed}, {records[3].id}, {records[4].id}"
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertEqual(
                self.record.get_ai_property_value("properties.many2many", None),
                [[records[0].id, records[0].display_name], [records[3].id, records[3].display_name]]
            )

        # Test missing model
        self.record.write({"properties": [{
            "type": "many2many",
            "name": "many2many",
            # comodel is missing
            "definition_changed": True,
            "ai": True,
            "system_prompt": system_prompt,
        }]})
        self.env.flush_all()
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertFalse(self.record.get_ai_property_value("properties.many2many", None))

    def test_ai_fields_validation_tags(self):
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": str(response)}

        system_prompt = 'This is my prompt 99 <t t-out="object.name"/>}}.'

        self.record.write({"properties": [{
            "type": "tags",
            "name": "tags",
            "definition_changed": True,
            "ai": True,
            "system_prompt": system_prompt,
            "tags": [["a", "A", 0], ["b", "B", 0], ["c", "C", 0], ["d", "D", 0]],
        }]})
        self.env.flush_all()

        response = "y,a,b,c,x"
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertEqual(self.record.get_ai_property_value("properties.tags", None), ["a", "b", "c"])

        # Test missing tags
        self.record.write({"properties": [{
            "type": "tags",
            "name": "tags",
            # tags is missing
            "definition_changed": True,
            "ai": True,
            "system_prompt": "Good prompt",
        }]})
        self.env.flush_all()
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            self.assertFalse(self.record.get_ai_property_value("properties.tags", None))

    def test_get_ai_property_value_new_record(self):
        """Test `get_ai_property_value` when the record does not exist."""
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            return {"content": f"response {params.get('prompt')}"}

        values = {"properties": [{"type": "char", "name": "char", "ai": True, "system_prompt": "This is my prompt <t t-out='1+1'/>", "value": "value"}]}
        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            value = self.env['test.ai.fields.model'].new().get_ai_property_value("properties.char", values)
        self.assertEqual(value, "response This is my prompt 2")

    def test_ai_field_many2one_insert_first_records(self):
        """Test that we take the most used records."""
        *__, invalid_value = self.env['res.partner'].create([
            # check if the name is added in the prompt
            {'name': 'valid <t t-out="object.name"/>'},
            {'name': 'valid <t t-out="1+1"/>'},
            {'name': 'invalid'},
        ])

        self.env["ir.model.fields"].create({
            "name": "x_ai_many2one",
            "model_id": self.env["ir.model"]._get("test.ai.fields.model").id,
            "ttype": "many2one",
            "relation": "res.partner",
            "ai": True,
            "system_prompt": "System Prompt",
            "domain": [['id', '!=', invalid_value.id]],
        })
        self.record.name = "name added"  # should not be added in prompt

        result = self.record.ai_find_default_records("res.partner", [['id', '!=', invalid_value.id]], "x_ai_many2one")
        self.assertNotIn("invalid", str(result))
        self.assertIn("valid", str(result))

        # Check that the most used records are inserted
        self.env['ir.config_parameter'].sudo().set_param('ai_field.insert_x_first_records', '3')
        less_used = self.env['res.partner'].create([
            {'name': 'less used 1'},
            {'name': 'less used 2'},
            {'name': 'less used 3'},
        ])
        self.env['test.ai.fields.model'].create([
            {'x_ai_many2one': less_used[0].id},
            {'x_ai_many2one': less_used[1].id},
            {'x_ai_many2one': less_used[2].id},
        ])
        most_used_records = self.env['res.partner'].create([
            {'name': 'more used 1'},
            {'name': 'more used 2'},
            {'name': 'more used 3'},
        ])
        self.env['test.ai.fields.model'].create([
            {'x_ai_many2one': most_used_records[0].id},
            {'x_ai_many2one': most_used_records[1].id},
            {'x_ai_many2one': most_used_records[2].id},
        ] * 5)

        result = self.record.ai_find_default_records("res.partner", [['id', '!=', invalid_value.id]], "x_ai_many2one")
        self.assertNotIn("less used", str(result))
        self.assertIn("more used 1", str(result))
        self.assertIn("more used 2", str(result))
        self.assertIn("more used 3", str(result))

        # Now we increased the limit, it should take unused records
        self.env['ir.config_parameter'].sudo().set_param('ai_field.insert_x_first_records', '3000')

        result = self.record.ai_find_default_records("res.partner", [['id', '!=', invalid_value.id]], "x_ai_many2one")
        self.assertIn("more used 1", str(result))
        self.assertIn("more used 2", str(result))
        self.assertIn("more used 3", str(result))
        self.assertIn("less used 1", str(result))
        self.assertIn("less used 2", str(result))
        self.assertIn("less used 3", str(result))

    def test_ai_field_many2one_properties_insert_first_records(self):
        """Test that we take the most used records."""
        self.env['ir.config_parameter'].sudo().set_param('ai_field.insert_x_first_records', '3000')
        self.record.write({"properties": [{
            "type": "many2one",
            "name": "many2one",
            "comodel": "res.partner",
            "definition_changed": True,
            "ai": True,
            "system_prompt": 'This is my m2o prompt',
            "domain": [('name', '!=', 'invalid')],
        }]})
        self.env.flush_all()

        self.env['res.partner'].create([
            {'name': 'valid'},
            {'name': 'invalid'},
        ])

        result = self.record.ai_find_default_records("res.partner", [('name', '!=', 'invalid')], "properties", "many2one")
        self.assertNotIn("invalid", str(result))
        self.assertIn("valid", str(result))

        self.env['ir.config_parameter'].sudo().set_param('ai_field.insert_x_first_records', '3')
        less_used = self.env['res.partner'].create([
            {'name': 'less used 1'},
            {'name': 'less used 2'},
            {'name': 'less used 3'},
        ])
        self.env['test.ai.fields.model'].create([
            {'parent_id': self.record.parent_id.id, 'properties': {'many2one': less_used[0].id}},
            {'parent_id': self.record.parent_id.id, 'properties': {'many2one': less_used[1].id}},
            {'parent_id': self.record.parent_id.id, 'properties': {'many2one': less_used[2].id}},
        ])
        most_used_records = self.env['res.partner'].create([
            {'name': 'more used 1'},
            {'name': 'more used 2'},
            {'name': 'more used 3'},
        ])
        self.env['test.ai.fields.model'].create([
            {'parent_id': self.record.parent_id.id, 'properties': {'many2one': most_used_records[0].id}},
            {'parent_id': self.record.parent_id.id, 'properties': {'many2one': most_used_records[1].id}},
            {'parent_id': self.record.parent_id.id, 'properties': {'many2one': most_used_records[2].id}},
        ] * 5)

        result = self.record.ai_find_default_records("res.partner", [('name', '!=', 'invalid')], "properties", "many2one")
        self.assertNotIn("less used", str(result))
        self.assertIn("more used 1", str(result))
        self.assertIn("more used 2", str(result))
        self.assertIn("more used 3", str(result))

        # If we increase the limit, use all records
        self.env['ir.config_parameter'].sudo().set_param('ai_field.insert_x_first_records', '3000')

        result = self.record.ai_find_default_records("res.partner", [('name', '!=', 'invalid')], "properties", "many2one")
        self.assertIn("more used 1", str(result))
        self.assertIn("more used 2", str(result))
        self.assertIn("more used 3", str(result))
        self.assertIn("less used 1", str(result))
        self.assertIn("less used 2", str(result))
        self.assertIn("less used 3", str(result))

from unittest.mock import patch

from odoo.tests import TransactionCase
from odoo.addons.iap.tools import iap_tools


class TestAiServerActions(TransactionCase):
    def test_ai_server_action(self):
        def _mocked_iap_jsonrpc(url, params, **kwargs):
            self.assertEqual(params["prompt"], "Write 1337")
            return {"content": "1337"}

        partner = self.env["res.partner"].create({"name": "Partner"})
        field = self.env["ir.model.fields"]._get(partner._name, "name").id
        action = self.env["ir.actions.server"].create(
            {
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "object_write",
                "name": "Test",
                "evaluation_type": "ai_computed",
                "ai_prompt": "Write 1337",
                "update_field_id": field,
            },
        )

        with patch.object(iap_tools, "iap_jsonrpc", _mocked_iap_jsonrpc):
            action.with_context(active_model=partner._name, active_id=partner.id).run()

        self.assertEqual(partner.name, "1337")

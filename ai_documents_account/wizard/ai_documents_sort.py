# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, Command, api, models
from odoo.addons.ai_fields.tools import ai_field_insert


class AiDocumentsSort(models.TransientModel):
    _inherit = "ai_documents.sort"

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)

        if "ai_sort_prompt" not in fields:
            return values

        if "folder_id" in values:
            existing_ir_action = self.env["ir.actions.server"].search(
                [("ai_autosort_folder_id", "=", values["folder_id"])],
                limit=1,
            )

            if existing_ir_action:
                # Don't set the default prompt
                return values

        if "ai_tool_ids" not in values:
            values["ai_tool_ids"] = [Command.set([])]

        create_vendor_bill = self.env.ref("documents_account.ir_actions_server_create_vendor_bill", raise_if_not_found=False)
        create_customer_invoice = self.env.ref("documents_account.ir_actions_server_create_customer_invoice", raise_if_not_found=False)
        prompt_lines = []
        if create_vendor_bill:
            prompt_lines.append(Markup(_("If it is a vendor bill, trigger the action to create a bill.")))
            values["ai_tool_ids"][0][2].append(create_vendor_bill.id)

        if create_customer_invoice:
            prompt_lines.append(
                Markup(_("If the customer is %s it means it is a customer invoice, trigger the Customer invoice action."))
                % ai_field_insert("company_id.name", _("Company > Name")),
            )
            values["ai_tool_ids"][0][2].append(create_customer_invoice.id)

        if values.get("ai_sort_prompt", ""):
            prompt_lines.append(_("Otherwise, %s", values.get("ai_sort_prompt", "")))

        # Change the default value for the prompt
        values["ai_sort_prompt"] = Markup("<br/>").join(prompt_lines)
        return values

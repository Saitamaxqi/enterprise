from odoo import fields, models


class VoipCall(models.Model):
    _inherit = "voip.call"

    application_count = fields.Integer(related="partner_id.applicant_ids.application_count")

    def voip_action_view_applications(self):
        self.ensure_one()
        similar_applicants = self.env["hr.applicant"].search(
            self.partner_id.applicant_ids._get_similar_applicants_domain(ignore_talent=True),
        )
        return {
            "name": self.env._("Applications"),
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "view_mode": "list,form",
            "domain": [("id", "in", similar_applicants.ids)],
            "context": {
                "active_test": False,
                "search_default_stage": 1,
                "default_applicant_ids": self.partner_id.applicant_ids.ids,
                "no_create_application_button": True,
            },
        }

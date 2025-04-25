from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    def _get_default_voip_provider(self):
        return self.env["voip.provider"].search([("company_id", "in", [self.env.company.id, False])], limit=1)

    voip_provider_id = fields.Many2one(
        "voip.provider", string="VoIP Provider",
        default=_get_default_voip_provider,
    )

    # Credentials for authentication to the PBX server
    voip_username = fields.Char(
        "VoIP username / Extension number",
        help="The username (typically the extension number) that will be used to register with the PBX server.",
    )
    voip_secret = fields.Char("VoIP secret", help="The password that will be used to register with the PBX server.")

    should_call_from_another_device = fields.Boolean(
        "Call from another device",
        help="""If enabled, placing a call in Odoo will transfer the call to the "External device number". Use this option to place the call in Odoo but handle it from another device - e.g. your desk phone.""",
    )
    external_device_number = fields.Char(
        "External device number",
        help="""If the "Call from another device" option is enabled, calls placed in Odoo will be transfered to this phone number.""",
    )

    should_auto_reject_incoming_calls = fields.Boolean(
        "Reject incoming calls",
        help="If enabled, incoming calls will be automatically declined in Odoo.",
    )

    # Mobile stuff
    how_to_call_on_mobile = fields.Selection(
        [("ask", "Ask"), ("voip", "VoIP"), ("phone", "Device's phone")],
        default="ask",
        string="How to place calls on mobile",
        help="""Choose the method to be used to place a call when using the mobile application:
            • VoIP: Always use the Odoo softphone
            • Device's phone: Always use the device's phone
            • Ask: Always ask whether the softphone or the device's phone must be used
        """,
        required=True,
    )

    do_not_disturb_until_dt = fields.Datetime(
        string="Do Not Disturb until",
        help="If set, VoIP will be in Do Not Disturb mode until this time."
    )

    @api.model
    def _format_settings(self, fields_to_format):
        res = super()._format_settings(fields_to_format)
        if "do_not_disturb_until_dt" in fields_to_format:
            res["do_not_disturb_until_dt"] = fields.Datetime.to_string(self.do_not_disturb_until_dt)
        return res

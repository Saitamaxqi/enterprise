from typing import Optional

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.mail.tools.discuss import Store


class VoipCall(models.Model):
    _name = "voip.call"
    _inherit = "voip.country.code.mixin"
    _description = """A phone call handled using the VoIP application"""

    phone_number = fields.Char(required=True, readonly=True)
    direction = fields.Selection(
        [
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
        ],
        default="outgoing",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("aborted", "Aborted"),
            ("calling", "Calling"),
            ("missed", "Missed"),
            ("ongoing", "Ongoing"),
            ("rejected", "Rejected"),
            ("terminated", "Terminated"),
        ],
        default="calling",
        index=True,
    )
    end_date = fields.Datetime()
    start_date = fields.Datetime()
    # Since activities are deleted from the database once marked as done, the
    # activity name is saved here in order to be preserved.
    activity_name = fields.Char(help="The name of the activity related to this phone call, if any.")
    partner_id = fields.Many2one("res.partner", "Contact", index=True)
    user_id = fields.Many2one("res.users", "Responsible", default=lambda self: self.env.uid, index=True)

    @api.depends("state", "partner_id.name")
    def _compute_display_name(self):
        def get_name(call):
            if call.activity_name:
                return call.activity_name
            if call.state == "aborted":
                return self.env._("Aborted call to %(phone_number)s", phone_number=call.phone_number)
            if call.state == "missed":
                return self.env._("Missed call from %(phone_number)s", phone_number=call.phone_number)
            if call.state == "rejected":
                if call.direction == "incoming":
                    return self.env._("Rejected call from %(phone_number)s", phone_number=call.phone_number)
                return self.env._("Rejected call to %(phone_number)s", phone_number=call.phone_number)
            if call.partner_id:
                if call.direction == "incoming":
                    return self.env._("Call from %(correspondent)s", correspondent=call.partner_id.name)
                return self.env._("Call to %(correspondent)s", correspondent=call.partner_id.name)
            if call.direction == "incoming":
                return self.env._("Call from %(phone_number)s", phone_number=call.phone_number)
            return self.env._("Call to %(phone_number)s", phone_number=call.phone_number)

        for call in self:
            call.display_name = get_name(call)

    @api.model
    def create_and_format(self, res_id: Optional[int] = None, res_model: Optional[str] = None, **kwargs) -> list:
        """Creates a call from the provided values and returns it formatted for
        use in JavaScript. If a record is provided via its id and model,
        introspects it for a recipient.
        """
        if res_id and res_model:
            related_record = self.env[res_model].browse(res_id)
            kwargs["partner_id"] = next(
                iter(related_record._mail_get_partners(introspect_fields=True)[related_record.id]),
                self.env["res.partner"],
            ).id
        calls = self.create(kwargs)
        return {"ids": [call.id for call in calls], "store_data": Store(calls, calls._get_voip_store_fields()).get_result()}

    @api.model
    def get_recent_phone_calls(
        self, search_terms: Optional[str] = None, offset: int = 0, limit: Optional[int] = None
    ):
        domain = Domain("user_id", "=", self.env.uid)
        if search_terms:
            search_fields = ["phone_number", "partner_id.name", "activity_name"]
            domain &= Domain.OR([Domain(field, "ilike", search_terms) for field in search_fields])
        calls = self.search(domain, offset=offset, limit=limit, order="create_date DESC")
        return Store(calls, calls._get_voip_store_fields()).get_result()

    @api.model
    def _get_number_of_missed_calls(self) -> int:
        domain = [("user_id", "=", self.env.uid), ("state", "=", "missed")]
        last_seen_phone_call = self.env.user.last_seen_phone_call
        if last_seen_phone_call:
            domain += [("id", ">", last_seen_phone_call.id)]
        return self.search_count(domain)

    def abort_call(self):
        self.state = "aborted"
        return Store(self, self._get_voip_store_fields()).get_result()

    def start_call(self):
        self.start_date = fields.Datetime.now()
        self.state = "ongoing"
        return Store(self, self._get_voip_store_fields()).get_result()

    def end_call(self, activity_name: Optional[str] = None):
        self.end_date = fields.Datetime.now()
        self.state = "terminated"
        if activity_name:
            self.activity_name = activity_name
        return Store(self, self._get_voip_store_fields()).get_result()

    def reject_call(self):
        self.state = "rejected"
        return Store(self, self._get_voip_store_fields()).get_result()

    def miss_call(self):
        self.state = "missed"
        return Store(self, self._get_voip_store_fields()).get_result()

    def get_contact_info(self):
        self.ensure_one()
        number = self.phone_number
        # Internal extensions could theoretically be one or two digits long.
        # phone_mobile_search doesn't handle numbers that short: do a regular
        # search for the exact match:
        if len(number) < 3:
            domain = [("phone", "=", number)]
        # 00 and + both denote an international prefix. phone_mobile_search will
        # match both indifferently.
        elif number.startswith(("+", "00")):
            domain = [("phone_mobile_search", "=", number)]
        # USA: Calls between different area codes are usually prefixed with 1.
        # Conveniently, the country code for the USA also happens to be 1, so we
        # just need to add the + symbol to format it like an international call
        # and match what's supposed to be stored in the database.
        elif number.startswith("1"):
            domain = [("phone_mobile_search", "=", f"+{number}")]
        else:
            domain = [("phone_mobile_search", "=", number)]
        partner = self.env["res.partner"].search(domain, limit=1)
        if not partner:
            return False
        self.partner_id = partner
        return Store(self, self._get_voip_store_fields()).get_result()

    def _get_voip_store_fields(self):
        return [
            "country_code_from_phone",
            "create_date",
            "direction",
            "display_name",
            "end_date",
            Store.One("partner_id", self.partner_id._voip_get_store_fields()),
            "phone_number",
            "start_date",
            "state",
        ]

    def _phone_get_number_fields(self):
        return ["phone_number"]

from typing import Optional

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.mail.tools.discuss import Store


class VoipCall(models.Model):
    _name = "voip.call"
    _inherit = ["mail.thread", "voip.country.code.mixin"]
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
        readonly=True,
    )
    end_date = fields.Datetime(readonly=True)
    start_date = fields.Datetime(readonly=True)
    duration = fields.Float(compute="_compute_duration", readonly=True)
    is_within_same_company = fields.Boolean(compute="_compute_is_within_same_company", store=True)
    # Since activities are deleted from the database once marked as done, the
    # activity name is saved here in order to be preserved.
    activity_name = fields.Char(help="The name of the activity related to this phone call, if any.")
    partner_id = fields.Many2one("res.partner", "Contact", index=True)
    user_id = fields.Many2one("res.users", "Responsible", default=lambda self: self.env.uid, index=True)
    country_id = fields.Many2one("res.country", compute="_compute_country_id", store=True)
    country_flag_url = fields.Char(related="country_id.image_url", string="Country Flag")
    provider_id = fields.Many2one(related="user_id.voip_provider_id", string="Provider", readonly=True)
    company_id = fields.Many2one(related="user_id.company_id", readonly=True)
    calls_count = fields.Integer(compute="_compute_calls_count")
    image_1920 = fields.Binary(related="partner_id.image_1920")
    avatar_128 = fields.Binary(related="partner_id.avatar_128")

    def _compute_calls_count(self):
        for rec in self:
            rec.calls_count = self.env["voip.call"].search_count(
                (rec.partner_id and ["|", ("phone_number", "=", rec.phone_number), ("partner_id", "=", rec.partner_id)])
                or [("phone_number", "=", rec.phone_number)]
            )

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

    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        for call in self:
            if call.start_date and call.end_date:
                call.duration = (call.end_date - call.start_date).total_seconds() / 3600
            else:
                call.duration = 0

    @api.depends("partner_id.commercial_partner_id", "user_id.partner_id.commercial_partner_id")
    def _compute_is_within_same_company(self):
        for call in self:
            user_company = call.user_id.partner_id.commercial_partner_id
            partner_company = call.partner_id.commercial_partner_id
            call.is_within_same_company = user_company and user_company == partner_company

    @api.depends("country_code_from_phone")
    def _compute_country_id(self):
        country_codes = set()
        for call in self:
            code = call.country_code_from_phone
            if code:
                country_codes.add(code.upper())
        countries = self.env["res.country"].search_read(
            [("code", "in", list(country_codes))],
            fields=["id", "code"],
        )
        country_id_by_iso_code = {country["code"].lower(): country["id"] for country in countries}

        for call in self:
            call.country_id = country_id_by_iso_code.get(call.country_code_from_phone, False)

    def write(self, vals):
        res = super().write(vals)
        if "partner_id" in vals:
            self.partner_id.phone = self.phone_number
        return res

    @api.model
    def create_and_format(
        self,
        phone_number: Optional[str] = None,
        partner_id: Optional[int] = None,
        direction: str = "outgoing",
        res_id: Optional[int] = None,
        res_model: Optional[str] = None,
    ) -> dict:
        """Creates a call from the provided values and returns it formatted for
        use in JavaScript. If a record is provided via its id and model,
        introspects it for a recipient.

        :param phone_number: The phone number to call
        :param partner_id: ID of the partner related to this call
        :param direction: Direction of the call ('incoming' or 'outgoing')
        :param res_id: Optional record ID to extract partner from
        :param res_model: Optional model name to extract partner from
        :return: Dictionary with created call IDs and formatted data
        """
        self.check_access("read")
        values = {
            "phone_number": phone_number,
            "partner_id": partner_id,
            "direction": direction,
            "state": "calling",
            "user_id": self.env.uid,
        }
        if res_id and res_model:
            related_record = self.env[res_model].browse(res_id)
            related_record.check_access("read")
            values["partner_id"] = next(
                iter(related_record._mail_get_partners(introspect_fields=True)[related_record.id]),
                self.env["res.partner"],
            ).id
        calls = self.sudo().create(values).sudo(False)
        return {
            "ids": [call.id for call in calls],
            "store_data": Store().add(calls, calls._get_voip_store_fields()).get_result(),
        }

    @api.model
    def get_recent_phone_calls(
        self, search_terms: Optional[str] = None, offset: int = 0, limit: Optional[int] = None
    ):
        domain = Domain("user_id", "=", self.env.uid)
        if search_terms:
            search_fields = ["phone_number", "partner_id.name", "activity_name"]
            domain &= Domain.OR([Domain(field, "ilike", search_terms) for field in search_fields])
        calls = self.search(domain, offset=offset, limit=limit, order="create_date DESC")
        return Store().add(calls, calls._get_voip_store_fields()).get_result()

    @api.model
    def _get_number_of_missed_calls(self) -> int:
        domain = [("user_id", "=", self.env.uid), ("state", "=", "missed")]
        last_seen_phone_call = self.env.user.last_seen_phone_call
        if last_seen_phone_call:
            domain += [("id", ">", last_seen_phone_call.id)]
        return self.search_count(domain)

    def abort_call(self):
        self.check_access("read")
        self.sudo().state = "aborted"
        return Store().add(self, self._get_voip_store_fields()).get_result()

    def start_call(self):
        self.check_access("read")
        calls_sudo = self.sudo()
        calls_sudo.start_date = fields.Datetime.now()
        calls_sudo.state = "ongoing"
        return Store().add(self, self._get_voip_store_fields()).get_result()

    def end_call(self, activity_name: Optional[str] = None):
        self.check_access("read")
        calls_sudo = self.sudo()
        calls_sudo.end_date = fields.Datetime.now()
        calls_sudo.state = "terminated"
        if activity_name:
            calls_sudo.activity_name = activity_name
        return Store().add(self, self._get_voip_store_fields()).get_result()

    def reject_call(self):
        self.check_access("read")
        self.sudo().state = "rejected"
        return Store().add(self, self._get_voip_store_fields()).get_result()

    def miss_call(self):
        self.check_access("read")
        self.sudo().state = "missed"
        return Store().add(self, self._get_voip_store_fields()).get_result()

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
        return Store().add(self, self._get_voip_store_fields()).get_result()

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

    def action_open_calls(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Calls",
            "res_model": "voip.call",
            "view_mode": "list,form",
            "domain": (
                self.partner_id
                and ["|", ("phone_number", "=", self.phone_number), ("partner_id", "=", self.partner_id.id)]
            )
            or [("phone_number", "=", self.phone_number)],
            "context": dict(self.env.context),
        }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, Command, fields, models
from odoo.fields import Domain
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _ai_tool_create_calendar_event(self, event_title, event_datetime, event_duration, attendee_names, summary):
        attendee_domain = Domain.FALSE
        for name in attendee_names:
            attendee_domain |= Domain([('name', 'ilike', name.strip())])
        attendee_ids = self.env['res.partner'].search(attendee_domain, limit=len(attendee_names))
        if not attendee_ids:
            raise UserError(_("The entered names %s are incorrect.", attendee_names))

        event_datetime = fields.Datetime.to_datetime(event_datetime)
        if event_datetime.date() < (fields.Date.today() + relativedelta(days=3)):
            raise UserError(_("The event date %s should be at least in 3 days from today", event_datetime))
        event_datetime = self._normalize_to_utc_and_remove_tzinfo(event_datetime)

        calendar_event = self.new({
            'name': event_title,
            'start': event_datetime,
            'duration': event_duration,
            'description': summary,
            'partner_ids': [Command.set([self.env.user.partner_id.id] + [attendee_id.id for attendee_id in attendee_ids])],
        })
        calendar_event._compute_stop()
        record = self.create(calendar_event._convert_to_write(calendar_event._cache))
        _logger.info("AI: Created calendar event #%s", record.id)
        return None

    def _normalize_to_utc_and_remove_tzinfo(self, event_datetime):
        # The event_datetime is in the user's timezone. It should be normalized to UTC. However, the tz is removed in the end as required by the ORM.
        user_timezone = pytz.timezone(self.env.user.tz)
        # Handle ambiguous/non-existent time related to DST. Assumption: Always use the new timezone: DST in case of DST start, STD in case of DST end.
        try:
            aware_dt = user_timezone.localize(event_datetime)
        except pytz.AmbiguousTimeError:
            aware_dt = user_timezone.localize(event_datetime, is_dst=False)
        except pytz.NonExistentTimeError:
            aware_dt = user_timezone.localize(event_datetime, is_dst=True)
        return aware_dt.astimezone(pytz.UTC).replace(tzinfo=None)

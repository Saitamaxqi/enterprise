# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, Command, fields, models
from odoo.fields import Domain
from odoo.addons.ai.utils.tools_schema.tools import register_ai_tool


class AITool(models.Model):
    _inherit = "ai.tool"

    @register_ai_tool({
        "description": "Create a calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                'event_title': {
                    'type': 'string',
                    'description': 'The title of the event.'
                },
                'attendee_names': {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    },
                    'description': 'The names of the event attendees.'
                },
                'event_datetime': {
                    'type': 'string',
                    'description': 'The date and time of the event in format YYYY-mm-dd HH:mm.',
                    'pattern': '^20\\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]) ([01][0-9]|2[0-3]):([0-5][0-9])$'
                },
                'event_duration': {
                    'type': 'number',
                    'description': 'The duration of the event in hours.'
                },
                'summary': {
                    'type': 'string',
                    'description': 'A summary of the purpose of the event.',
                }
            },
            "required": ["event_title", "attendee_names", "event_datetime", "event_duration"],
        },
    })
    def _create_calendar_event(self, event_title, event_datetime, event_duration, attendee_names, summary):
        CalendarEvent = self.env['calendar.event']
        attendee_domain = Domain.FALSE
        for name in attendee_names:
            attendee_domain |= Domain([('name', 'ilike', name.strip())])
        attendee_ids = self.env['res.partner'].search(attendee_domain, limit=len(attendee_names))
        if not attendee_ids:
            return _("The entered names %s are incorrect.", attendee_names)

        event_datetime = fields.Datetime.to_datetime(event_datetime)
        if event_datetime.date() < (fields.Date.today() + relativedelta(days=3)):
            return _("The event date %s should be at least in 3 days from today", event_datetime)
        event_datetime = self._normalize_to_utc_and_remove_tzinfo(event_datetime)

        calendar_event = CalendarEvent.new({
            'name': event_title,
            'start': event_datetime,
            'duration': event_duration,
            'description': summary,
            'partner_ids': [Command.set([self.env.user.partner_id.id] + [attendee_id.id for attendee_id in attendee_ids])],
        })
        calendar_event._compute_stop()
        CalendarEvent.create(calendar_event._convert_to_write(calendar_event._cache))

        success_message = _(
            "The event has been scheduled on %(event_datetime)s."
            "The following attendees have been invited: %(invited_attendee_names)s."
            "Attendees whose names aren't listed weren't found in the system and thus couldn't be invited and should be invited manually.",
            event_datetime=event_datetime,
            invited_attendee_names=', '.join(attendee_ids.mapped('name'))
        )
        return success_message

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

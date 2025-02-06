import pytz
from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models
from odoo.fields import Domain


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event']

    def create_calendar_event(self):
        event_title = self.env.context.get('event_title')

        attendee_names = self.env.context.get('attendee_names').split(',')
        attendee_domain = Domain.FALSE
        for name in attendee_names:
            attendee_domain |= Domain([('name', 'ilike', name.strip())])
        attendee_ids = self.env['res.partner'].search(attendee_domain, limit=len(attendee_names))
        if not attendee_ids:
            return f"The entered names {attendee_names} are incorrect."

        event_datetime = fields.Datetime.to_datetime(self.env.context.get('event_datetime'))
        if event_datetime.date() < (fields.Date.today() + relativedelta(days=3)):
            return f"The event date {event_datetime} should be at least in 3 days from today"
        event_datetime = self._normalize_to_utc_and_remove_tzinfo(event_datetime)

        duration = self.env.context.get('event_duration')
        summary = self.env.context.get('summary', '')
        # Use new instead of create so that compute methods are triggered.
        calendar_event = self.new({
            'name': event_title,
            'start': event_datetime,
            'duration': duration,
            'description': summary,
            'partner_ids': [Command.set([self.env.user.partner_id.id] + [attendee_id.id for attendee_id in attendee_ids])],
        })
        calendar_event._compute_stop()
        self.create(calendar_event._convert_to_write(calendar_event._cache))
        return self.env.context.get('result_prompt').format(attendee_names=attendee_ids.mapped('name'), event_datetime=event_datetime)

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

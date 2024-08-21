# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[('whatsapp', 'WhatsApp')])
    template_ref = fields.Reference(ondelete={'whatsapp.template': 'cascade'}, selection_add=[('whatsapp.template', 'WhatsApp')])

    @api.constrains('template_ref')
    def _check_whatsapp_template_phone_field(self):
        for record in self:
            if record.notification_type == 'whatsapp' and not record.template_ref.phone_field:
                raise ValidationError(_('Whatsapp Templates in Events must have a phone field set.'))

    def _compute_notification_type(self):
        super()._compute_notification_type()
        social_schedulers = self.filtered(lambda scheduler: scheduler.template_ref and scheduler.template_ref._name == 'whatsapp.template')
        social_schedulers.notification_type = 'whatsapp'

    def _execute_event_based_for_registrations(self, registrations):
        # no template / wrong template -> ill configured, skip and avoid crash
        if self.notification_type == "whatsapp":
            if not self._filter_wa_template_ref():
                return False
            self.env['whatsapp.composer'].with_context(
                {'active_ids': registrations.ids}
            ).create({
                'res_model': 'event.registration',
                'wa_template_id': self.template_ref.id
            })._send_whatsapp_template(force_send_by_cron=True)
            return True
        return super()._execute_event_based_for_registrations(registrations)

    def _filter_wa_template_ref(self):
        """ Check for valid template reference: existing, working template """
        wa_schedulers = self.filtered(lambda s: s.notification_type == "whatsapp")
        if not wa_schedulers:
            return self.browse()
        existing_templates = wa_schedulers.template_ref.exists()
        missing = wa_schedulers.filtered(lambda s: s.template_ref not in existing_templates)
        for scheduler in missing:
            _logger.warning(
                "Cannot process scheduler %s (event %s) as it refers to non-existent whatsapp template %s",
                scheduler.id, scheduler.event_id.name, scheduler.template_ref.id
            )
        invalid = wa_schedulers.filtered(
            lambda scheduler: scheduler not in missing
                              and (scheduler.template_ref._name != "whatsapp.template" or scheduler.template_ref.status != 'approved')
        )
        for scheduler in invalid:
            _logger.warning(
                "Cannot process scheduler %s (event %s) as it refers to invalid whatsapp template %s (ID %s)",
                scheduler.id, scheduler.event_id.name, scheduler.template_ref.name, scheduler.template_ref.id)
        return self - missing - invalid

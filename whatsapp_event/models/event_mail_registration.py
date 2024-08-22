# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import models

_logger = logging.getLogger(__name__)


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def _execute_on_registrations(self):
        todo = self.filtered(
            lambda r: r.scheduler_id.notification_type == "whatsapp"
        )
        # Group todo by templates so if one tempalte then we can send in one shot
        tosend_by_template = defaultdict(list)
        for registration in todo:
            tosend_by_template.setdefault(registration.scheduler_id.template_ref.id, [])
            tosend_by_template[registration.scheduler_id.template_ref.id].append(registration.registration_id.id)

        # Create whatsapp composer and send message by cron
        failed_registration_ids = []
        for wa_template_id, registration_ids in tosend_by_template.items():
            try:
                self.env['whatsapp.composer'].with_context({
                    'active_ids': registration_ids,
                    'active_model': 'event.registration',
                }).create({
                    'wa_template_id': wa_template_id,
                })._send_whatsapp_template(force_send_by_cron=True)
            except Exception as e:  # noqa: BLE001 we should never raise and rollback here
                _logger.warning('An issue happened when sending WhatsApp template ID %s. Received error %s', wa_template_id, e)
                failed_registration_ids += registration_ids

        # mark as sent only if really sent
        todo.filtered(
            lambda reg: reg.registration_id.id not in failed_registration_ids
        ).mail_sent = True
        return super(EventMailRegistration, self - todo)._execute_on_registrations()

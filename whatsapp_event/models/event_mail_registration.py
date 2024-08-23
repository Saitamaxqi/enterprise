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
        # Create whatsapp composer and send message by cron
        failed_registration_ids = []
        for scheduler, reg_mails in todo.grouped('scheduler_id').items():
            try:
                scheduler._send_whatsapp(reg_mails.registration_id)
            except Exception as e:  # noqa: BLE001 we should never raise and rollback here
                _logger.warning('An issue happened when sending WhatsApp template ID %s. Received error %s', scheduler.template_ref.id, e)
                failed_registration_ids += reg_mails.registration_id

        # mark as sent only if really sent
        todo.filtered(
            lambda reg: reg.registration_id.id not in failed_registration_ids
        ).mail_sent = True
        return super(EventMailRegistration, self - todo)._execute_on_registrations()

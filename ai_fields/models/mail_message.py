# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _ai_format_mail_messages(self):
        if not self:
            return ""

        message_subtype = self.env.ref('mail.mt_comment')
        values = [
            {
                "subject": message.subject,
                "content": message.body,
                "author": bool(message.author_id) and {
                    "id": message.author_id.id,
                    "name": message.author_id.display_name,
                },
                "date": message.create_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }
            for message in self
            if message.message_type in ('comment', 'email', 'email_outgoing')
            and message.subtype_id == message_subtype
        ]
        return json.dumps({"messages": values})

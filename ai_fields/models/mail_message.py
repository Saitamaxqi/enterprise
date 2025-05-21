# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _ai_format(self, files_dict):
        """When a message field is inserted in an AI prompt, the subject, body, date and author
        of the mail messages are sent to the LLM
        """
        msg_subtype = self.env.ref('mail.mt_comment')
        msg_types = ('comment', 'email', 'email_outgoing')
        return self.filtered(
            lambda m: m.message_type in msg_types and m.subtype_id == msg_subtype
        )._ai_read(['subject', 'body', 'author_id', 'date'], files_dict)

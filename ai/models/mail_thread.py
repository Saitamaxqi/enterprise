# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class MailThread(models.AbstractModel):
    _name = 'mail.thread'
    _inherit = ['mail.thread']
    _description = 'AI features for mail thread'

    def _ai_serialize_messages_data(self):
        chatter_messages = []
        for message in self.message_ids:
            chatter_messages.append(
                f"({message.subtype_id.name}) {message.author_id.name}: {message.body.striptags().strip() if message.body else ''}, "
            )
        # the messages are stored from newest to oldest - reverse them so they are formatted like the conversation history
        chatter_messages = " ".join(list(reversed(chatter_messages)))

        return chatter_messages

    def _ai_initialise_context(
        self, caller_component, composer_default_prompt, text_selection=None, front_end_info=None
    ):
        context = super()._ai_initialise_context(
            caller_component, composer_default_prompt, text_selection, front_end_info
        )

        # If required, pass the previous chatter messages to the model's context
        if caller_component in [
            "html_field_composer",
            "composer_ai_button",
            "chatter_ai_button",
        ]:
            context.insert(
                -3,  # we insert the message at this index in order for the chatter conversation to be added right after the records info JSON
                {
                    "role": "system",
                    "content": f"The previous chatter correspondance, from oldest to newest, for this record is this: {self._ai_serialize_messages_data()}",
                }
            )

        return context

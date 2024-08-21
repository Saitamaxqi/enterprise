# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[('social_post', 'Social Post')])
    template_ref = fields.Reference(ondelete={'social.post.template': 'cascade'}, selection_add=[('social.post.template', 'Social Post')])

    @api.constrains('template_ref', 'interval_type')
    def _check_interval_type(self):
        """Cannot select "after_sub" if the notification type is "social_post"."""
        for mail in self:
            if mail.notification_type == 'social_post' and mail.interval_type == 'after_sub':
                raise UserError(_('As social posts have no recipients, they cannot be triggered by registrations.'))

    def _compute_notification_type(self):
        super()._compute_notification_type()
        social_schedulers = self.filtered(lambda scheduler: scheduler.template_ref and scheduler.template_ref._name == 'social.post.template')
        social_schedulers.notification_type = 'social_post'

    def _execute_event_based(self):
        social_schedulers = self.filtered(lambda scheduler: scheduler.notification_type == 'social_post')

        social_posts_values = [
            scheduler.template_ref._prepare_social_post_values()
            for scheduler in social_schedulers
            if scheduler.template_ref.account_ids
        ]

        if social_posts_values:
            self.env['social.post'].sudo().create(social_posts_values)._action_post()

        for scheduler in social_schedulers:
            scheduler.update({
                'mail_done': True,
                'mail_count_done': len(scheduler.template_ref.account_ids),
            })

        return super(EventMailScheduler, self - social_schedulers)._execute_event_based()

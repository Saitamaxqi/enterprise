from odoo import fields, models, _


class DocumentsAccessInvite(models.TransientModel):
    _name = 'documents.access.invite'
    _description = "Documents Access Invite"

    document_id = fields.Many2one('documents.document', string="Documents", required=True)
    partner_ids = fields.Many2many('res.partner', required=True)
    role = fields.Selection(
        [('view', 'Viewer'), ('edit', 'Editor')],
        string='Role', default='view', required=True)
    notify = fields.Boolean("Notify", default=True)
    notify_message = fields.Html("Notification Message")
    access_url = fields.Char(related="document_id.access_url")

    def action_invite_members(self):
        self.document_id.action_update_access_rights(
            partners={
                partner: (self.role, None)
                for partner in self.partner_ids
            }
        )

        if self.notify and (share_template := self.env.ref('documents.mail_template_document_share', raise_if_not_found=False)):
            share_template.with_context(message=self.notify_message).send_mail_batch(
                self.document_id.access_ids.filtered(lambda acc: acc.partner_id in self.partner_ids).ids
            )

        message = (
            _('%s members added successfully.', len(self.partner_ids))
            if len(self.partner_ids) > 1
            else _('Member added successfully.')
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Successfully Shared'),
                'message': message,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

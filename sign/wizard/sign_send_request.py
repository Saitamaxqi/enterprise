# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command
from odoo.exceptions import UserError


class SignSendRequest(models.TransientModel):
    _name = 'sign.send.request'
    _description = 'Sign send request'

    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search(
            [
                ('model', '!=', 'sign.request'),
                ('is_mail_thread', '=', 'True'),
            ]
        )]

    activity_id = fields.Many2one('mail.activity', 'Linked Activity', readonly=True)
    reference_doc = fields.Reference(string="Linked to", selection='_selection_target_model', readonly=True)
    has_default_template = fields.Boolean()
    available_template_ids = fields.Many2many(comodel_name='sign.template', compute='_compute_available_template_ids')
    template_id = fields.Many2one('sign.template', string="Sign Template", ondelete='cascade')

    signer_ids = fields.One2many('sign.send.request.signer', 'sign_send_request_id', string="Signers", compute='_compute_signer_ids', store=True)
    set_sign_order = fields.Boolean(string="Signing Order",
                                    help="""Specify the order for each signer. The signature request only gets sent to \
                                    the next signers in the sequence when all signers from the previous level have \
                                    signed the document.
                                    """)
    signer_id = fields.Many2one('res.partner', string="Send To")
    signers_count = fields.Integer(compute='_compute_signers_count')
    cc_partner_ids = fields.Many2many('res.partner', string="Copy to", help="Contacts in copy will be notified by email once the document is either fully signed or refused.")
    is_user_signer = fields.Boolean(compute='_compute_is_user_signer')

    subject = fields.Char(string="Subject", compute='_compute_subject', store=True)
    message = fields.Html("Message", help="Message to be sent to signers of the specified document")
    message_cc = fields.Html("CC Message", help="Message to be sent to contacts in copy of the signed document")
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    filename = fields.Char("Filename", compute='_compute_filename', store=True)

    validity = fields.Date(string='Valid Until', default=lambda self: fields.Date.today() + relativedelta(months=6), help="Leave empty for requests without expiration.")
    reminder_enabled = fields.Boolean(default=False)
    reminder = fields.Integer(string='Reminder', default=7)
    certificate_reference = fields.Boolean(string="Certificate Reference", default=False, help="If checked, the unique certificate reference will be added on the final signed document.")

    @api.onchange('validity')
    def _onchange_validity(self):
        if self.validity and self.validity < fields.Date.today():
            raise UserError(self.env._('Request expiration date must be set in the future.'))

    @api.onchange('reminder')
    def _onchange_reminder(self):
        if self.reminder > 365:
            self.reminder = 365

    def _get_default_signer(self):
        """Helper method to define default signer (see hr_recruitment_sign/wizard/sign_send_request.py).
        """
        if self.reference_doc or self.env.context.get('default_reference_doc'):
            ref = self.reference_doc
            # If the reference document has a direct partner, such as in the contacts module.
            if ref._name == 'res.partner':
                return ref.id

            # return the partner_id of the reference document
            partner = 'partner_id' in ref and ref.partner_id
            if partner:
                return partner.id

            # If the reference document has an user_id, some modules like MRP etc.
            user = 'user_id' in ref and ref.user_id
            if user and user.partner_id:
                return user.partner_id.id

            # If the reference document has an employee_id, some modules like hr_recruitment, expense, etc.
            employee = 'employee_id' in ref and ref.employee_id
            if employee and employee.work_contact_id:
                return employee.work_contact_id.id

        return self.env.context.get("default_signer_id", self.env.user.partner_id.id)

    @api.depends('template_id', 'set_sign_order', 'template_id.sign_item_ids')
    def _compute_signer_ids(self):
        default_signer = self._get_default_signer()
        for wiz in self:
            template = wiz.template_id
            roles = template.sign_item_ids.responsible_id.sorted()
            signer_ids = []
            if (self.signer_ids and len(self.signer_ids) == len(roles)):
                # update when we set the order
                signer_ids = [(0, 0, {
                    'role_id': signer.role_id.id,
                    'partner_id': signer.partner_id.id,
                    'mail_sent_order': default_signing_order + 1 if wiz.set_sign_order else 1
                }) for default_signing_order, signer in enumerate(self.signer_ids)]
            else:
                for default_signing_order, role in enumerate(roles):
                    # First signer logic
                    if default_signing_order == 0:
                        # If role has assign_to, use it; else use default_signer
                        partner_id = role.assign_to.id if role.assign_to else default_signer
                    else:
                        # For other roles, check assign_to
                        partner_id = role.assign_to.id if role.assign_to else False
                    signer_vals = {
                        'role_id': role.id,
                        'partner_id': partner_id,
                        'mail_sent_order': default_signing_order + 1 if wiz.set_sign_order else 1,
                    }
                    signer_ids.append((0, 0, signer_vals))
            wiz.signer_ids = [(5, 0, 0)] + signer_ids

    @api.depends('signer_ids')
    def _compute_signers_count(self):
        for wiz in self:
            wiz.signers_count = len(wiz.signer_ids)

    @api.depends('template_id', 'reference_doc')
    def _compute_display_name(self):
        for wiz in self:
            display_name = self.env._("Sign Request ")
            if wiz.reference_doc:
                display_name = self.env._("Sign Request - %s", wiz.reference_doc.display_name)
            wiz.display_name = display_name

    @api.depends('template_id', 'reference_doc')
    def _compute_subject(self):
        for wiz in self:
            subject = self.env._("Signature Request")
            if wiz.reference_doc:
                subject = self.env._("Signature Request - %s", wiz.reference_doc.display_name or '')
            elif wiz.template_id:
                subject = self.env._("Signature Request - %(file_name)s", file_name=wiz.template_id.name)
            wiz.subject = subject

    @api.depends('template_id', 'reference_doc')
    def _compute_filename(self):
        for wiz in self:
            filename = self.env._("Sign Request")
            if wiz.reference_doc:
                filename = self.env._("Sign Request - %s", wiz.reference_doc.display_name)
            elif wiz.template_id:
                filename = wiz.template_id.display_name
            wiz.filename = filename

    @api.depends('signer_ids.partner_id', 'signer_id', 'signers_count')
    def _compute_is_user_signer(self):
        if self.signers_count and self.env.user.partner_id in self.signer_ids.mapped('partner_id'):
            self.is_user_signer = True
        elif not self.signers_count and self.env.user.partner_id == self.signer_id:
            self.is_user_signer = True
        else:
            self.is_user_signer = False

    @api.depends('reference_doc')
    def _compute_available_template_ids(self):
        non_specific_templates = self.env['sign.template'].search([('model_id', '=', False)])._filtered_access('read')
        template_by_model = {}
        if self.reference_doc:
            model_names = [ref._name for ref in self.reference_doc if self.reference_doc]
            # unprivilegied user don't have access to ir.model
            model_ids = self.env['ir.model'].sudo().search([('model', 'in', model_names)]).ids
            res = self.env['sign.template']._read_group(
                [('model_id', 'in', model_ids)],
                groupby=['model_id'],
                aggregates=['id:recordset'],
            )
            for model, template in res:
                template_by_model[model.id] = template
        for wiz in self:
            all_template_ids = non_specific_templates.ids
            if wiz.reference_doc:
                model = self.env['ir.model'].sudo()._get(wiz.reference_doc._name)
                other_templates = template_by_model.get(model.id, self.env['sign.template'])
                all_template_ids += other_templates.ids
            wiz.available_template_ids = [Command.set(all_template_ids)]

    # ==== Business methods ====

    def _activity_done(self):
        signatories = self.signer_id.name or self.signer_ids.partner_id.mapped('name')
        feedback = self.env._('Signature requested for template: %(template)s\nSignatories: %(signatories)s', template=self.template_id.name, signatories=signatories)
        self.activity_id._action_done(feedback=feedback)

    def create_request(self):
        template_id = self.template_id.id
        if self.signers_count:
            signers = [{'partner_id': signer.partner_id.id, 'role_id': signer.role_id.id, 'mail_sent_order': signer.mail_sent_order} for signer in self.signer_ids]
        else:
            signers = [{'partner_id': self.signer_id.id, 'role_id': self.env.ref('sign.sign_item_role_default').id, 'mail_sent_order': self.signer_ids.mail_sent_order}]
        cc_partner_ids = self.cc_partner_ids.ids
        reference = self.filename or self.template_id.name
        subject = self.subject
        message = self.message
        message_cc = self.message_cc
        attachment_ids = self.attachment_ids
        reference_doc = None
        if self.reference_doc:
            reference_doc = f"{self.reference_doc._name},{self.reference_doc.id}"
        sign_request = self.env['sign.request'].create({
            'template_id': template_id,
            'request_item_ids': [Command.create({
                'partner_id': signer['partner_id'],
                'role_id': signer['role_id'],
                'mail_sent_order': signer['mail_sent_order'],
            }) for signer in signers],
            'reference': reference,
            'subject': subject,
            'message': message,
            'message_cc': message_cc,
            'attachment_ids': [Command.set(attachment_ids.ids)],
            'validity': self.validity,
            'reminder': self.reminder,
            'reminder_enabled': self.reminder_enabled,
            'reference_doc': reference_doc,
            'certificate_reference': self.certificate_reference,
        })
        sign_request.message_subscribe(partner_ids=cc_partner_ids)
        return sign_request

    def send_request(self):
        self.ensure_one()
        request = self.create_request()
        self._create_request_log_note(request)
        if self.activity_id:
            self._activity_done()

        current_partner_id = self.env.user.partner_id.id
        # Check if the current user's partner is one of the signers
        if any(signer.partner_id.id == current_partner_id for signer in self.signer_ids):
            return request.go_to_document()
        if not self.reference_doc:
            return self.env['ir.actions.actions']._for_xml_id('sign.sign_request_action')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._("Request sent successfully"),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def _create_request_log_note(self, request):
        if request.reference_doc:
            model = request.reference_doc and self.env['ir.model']._get(request.reference_doc._name)
            if model.is_mail_thread:
                body = self.env._("A signature request has been linked to this document: %s", request._get_html_link())
                request.reference_doc.message_post(body=body)
                body = self.env._("%s has been linked to this sign request.", request.reference_doc._get_html_link())
                request.message_post(body=body)

    def sign_directly(self):
        self.ensure_one()
        request = self.create_request()
        if self.activity_id:
            self._activity_done()
        if self.env.context.get('sign_all'):
            # Go back to document if it exists
            return request.go_to_signable_document(request.request_item_ids)
        return request.go_to_signable_document()

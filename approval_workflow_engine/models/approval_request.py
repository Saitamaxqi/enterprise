from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Request Reference',
        readonly=True,
        copy=False,
        default='New'
    )

    workflow_id = fields.Many2one(
        'approval.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )

    res_model = fields.Char(
        string='Document Model',
        readonly=True
    )

    res_id = fields.Integer(
        string='Document ID',
        readonly=True
    )

    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        default=lambda self: self.env.user,
        readonly=True,
    )

    stage_id = fields.Many2one(
        'approval.stage',
        string='Current Stage',
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Approval'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, readonly=True)

    log_ids = fields.One2many(
        'approval.log',
        'request_id',
        string='Approval Logs'
    )

    can_current_user_approve = fields.Boolean(
        string='Can Current User Approve',
        compute='_compute_can_current_user_approve',
        store=False
    )
    current_approver_user_ids = fields.Many2many(
    'res.users',
    string='Current Approvers',
    compute='_compute_current_approver_user_ids',
    store=True
)
    @api.depends(
    'stage_id',
    'stage_id.group_ids',
    'stage_id.group_ids.group_id'
)
    def _compute_current_approver_user_ids(self):
            self._update_current_approver_users()
    def _update_current_approver_users(self):
        for record in self:
            valid_users = self.env['res.users']

        if record.stage_id:
            for approval_group in record.stage_id.group_ids.filtered('active'):
                group = approval_group.group_id
                if not group:
                    continue

                self.env.cr.execute("""
                    SELECT uid
                    FROM res_groups_users_rel
                    WHERE gid = %s
                """, (group.id,))

                user_ids = [row[0] for row in self.env.cr.fetchall()]
                users = self.env['res.users'].browse(user_ids).filtered('active')

                for user in users:
                    if record._check_group_filters(approval_group, user=user):
                        valid_users |= user

        record.current_approver_user_ids = [(6, 0, valid_users.ids)]

    @api.depends(
        'stage_id',
        'stage_id.group_ids',
        'stage_id.group_ids.group_id'
    )
    def _compute_can_current_user_approve(self):
        current_user = self.env.user

        for record in self:
            can_approve = False
            
            if not record.stage_id:
                record.can_current_user_approve = False
                continue

            stage_groups = record.stage_id.group_ids.filtered('active')

            if stage_groups:
                for approval_group in stage_groups:
                    xml_id_dict = approval_group.group_id.get_external_id()
                    xml_id = xml_id_dict.get(approval_group.group_id.id)
                    if xml_id and current_user.has_group(xml_id):
                        if record._check_group_filters(approval_group):
                            can_approve = True
                            break
            else:
                if current_user.has_group('base.group_system'):
                    can_approve = True

            record.can_current_user_approve = can_approve

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or 'New'
        return super().create(vals_list)

    def _resolve_dynamic_value(self, filter_value, user=None):
        user = user or self.env.user

        if not (isinstance(filter_value, str) and filter_value.startswith('{user.') and filter_value.endswith('}')):
            return filter_value

        attr_path = filter_value[6:-1]

        try:
            obj = user
            for attr in attr_path.split('.'):
                obj = getattr(obj, attr)

            if hasattr(obj, 'id'):
                return obj.id

            return obj
        except Exception:
            return filter_value

    def _convert_filter_value(self, record_value, filter_value, user=None):
        filter_value = self._resolve_dynamic_value(filter_value, user=user)

        if type(filter_value) == type(record_value):
            return filter_value

        if isinstance(record_value, bool):
            return str(filter_value).strip().lower() in ['true', '1', 'yes']

        if isinstance(record_value, int):
            return int(filter_value)

        if isinstance(record_value, float):
            return float(filter_value)

        return str(filter_value)

    def _evaluate_filter(self, record_value, operator, filter_value):
        if operator == '=':
            return record_value == filter_value
        if operator == '!=':
            return record_value != filter_value
        if operator == '>':
            return record_value > filter_value
        if operator == '<':
            return record_value < filter_value
        if operator == '>=':
            return record_value >= filter_value
        if operator == '<=':
            return record_value <= filter_value
        return False

    def _check_group_filters(self, approval_group, user=None):
        self.ensure_one()

        filters = approval_group.filter_ids.filtered('active')
        if not filters:
            return True

        document = self.env[self.res_model].browse(self.res_id)
        if not document.exists():
            return False

        for filter_rec in filters:
            field_path = filter_rec.field_name.split('.')
            record_value = document

            for part in field_path:
                if not hasattr(record_value, part):
                    return False
                record_value = record_value[part]

            if hasattr(record_value, 'id'):
                record_value = record_value.id

            try:
                converted_value = self._convert_filter_value(
                    record_value,
                    filter_rec.value,
                    user=user
                )
            except Exception:
                return False

        if not self._evaluate_filter(record_value, filter_rec.operator, converted_value):
            return False

        return True

    def action_submit(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))

            first_stage = self.env['approval.stage'].sudo().search(
                [('workflow_id', '=', record.workflow_id.id)],
                order='sequence asc',
                limit=1
            )

            if not first_stage:
                raise UserError(_('This workflow has no stages configured.'))

            record_sudo = record.sudo()
            record_sudo.stage_id = first_stage.id
            record_sudo.state = 'waiting'
            record_sudo._update_current_approver_users()

            record_sudo.message_post(body=_('Approval request submitted.'))
            record_sudo._notify_approvers()


    def action_open_approve_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Request'),
            'res_model': 'approval.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_action_type': 'approved',
            }
        }

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Request'),
            'res_model': 'approval.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_action_type': 'rejected',
            }
        }

    def action_approve(self, comment=None):
        for record in self:
            if record.state not in ['waiting', 'in_progress']:
                raise UserError(_('Only requests waiting for approval can be approved.'))

            if not record.can_current_user_approve:
                raise UserError(_('You are not allowed to approve this request.'))

            comment = (comment or '').strip()
            record_sudo = record.sudo()

            self.env['approval.log'].sudo().create({
                'request_id': record.id,
                'user_id': self.env.user.id,
                'action': 'approved',
                'comment': comment,
            })

            record_sudo.message_post(
                body=_('Approved by %s%s') % (
                    self.env.user.name,
                    ('<br/>Comment: %s' % comment) if comment else ''
                )
            )

            next_stage = self.env['approval.stage'].sudo().search([
                ('workflow_id', '=', record.workflow_id.id),
                ('sequence', '>', record.stage_id.sequence)
            ], order='sequence asc', limit=1)

            if next_stage:
                record_sudo.stage_id = next_stage
                record_sudo.state = 'in_progress'
                record_sudo._update_current_approver_users()

                record_sudo.message_post(
                    body=_('Approval moved to next stage: %s') % next_stage.name
                )

                record_sudo._mark_approver_activity_done()
                record_sudo._notify_approvers()
            else:
                record_sudo.state = 'approved'
                record_sudo._update_current_approver_users()

                record_sudo.message_post(
                    body=_('Approval request fully approved.')
                )

                record_sudo._mark_approver_activity_done()
                record_sudo._on_approval_completed(True)


    def action_reject(self, comment=None):
        for record in self:
            if record.state not in ['waiting', 'in_progress']:
                raise UserError(_('Only requests waiting for approval can be rejected.'))

            if not record.can_current_user_approve:
                raise UserError(_('You are not allowed to reject this request.'))

            comment = (comment or '').strip()

            if not comment:
                raise UserError(_('A comment is required when rejecting a request.'))

            record_sudo = record.sudo()

            self.env['approval.log'].sudo().create({
                'request_id': record.id,
                'user_id': self.env.user.id,
                'action': 'rejected',
                'comment': comment,
            })

            record_sudo.state = 'rejected'
            record_sudo._update_current_approver_users()

            record_sudo.message_post(
                body=_('Rejected by %s<br/>Comment: %s') % (
                    self.env.user.name,
                    comment
                )
            )

            record_sudo._mark_approver_activity_done()
            record_sudo._on_approval_completed(False)



    def _on_approval_completed(self, approved):
        """Call completion callback on the related document if it exists"""
        for record in self:
            if record.res_model and record.res_id:
                try:
                    document = self.env[record.res_model].browse(record.res_id)
                    if document.exists() and hasattr(document, '_on_approval_completed'):
                        document._on_approval_completed(approved)
                except Exception:
                    # Silently ignore errors to not break the approval process
                    pass

    # Notification methods

    def _notify_approvers(self):
        for record in self:
         record._update_current_approver_users()

        for user in record.current_approver_user_ids:
            record.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                note=_('Approval required for request %s at stage: %s') % (
                    record.name,
                    record.stage_id.name
                ),
            )

    def _mark_approver_activity_done(self):
        """Mark the current user's pending approval activities as done."""
        for record in self:
            activities = record.activity_ids.filtered(
                lambda a: a.user_id == self.env.user
                and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
            )
            activities.action_done()

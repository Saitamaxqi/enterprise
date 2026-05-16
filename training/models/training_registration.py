from datetime import date
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.tools.convert import relativedelta

class TrainingRegistration(models.Model):
    _name = 'training.registration'
    _description = 'Training Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    trainee_id = fields.Many2one(
        'hr.employee', 
        string="Trainee",
        readonly=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        )
    course_id = fields.Many2one('training.courses', string='Course', required=True)
    course_serial_number = fields.Char(string= 'Course Serial Number',related='course_id.serial_number',readonly=True)
    course_name = fields.Char(string='Course Name', related='course_id.name',readonly=True)
    course_desc = fields.Text(string='Course Description', related='course_id.description',readonly=True)
    teacher_name = fields.Char(string='Teacher Name', related='course_id.teacher_id.name',readonly=True)
    start_date = fields.Date(string='Start Date', related='course_id.start_date',readonly=True)
    end_date = fields.Date(string='End Date', related='course_id.end_date',readonly=True)
    number_of_days = fields.Integer(string='Number of Days', related='course_id.number_of_days',readonly=True)
    time = fields.Float(string='Time (hours)', related='course_id.time',readonly=True)
    room_name = fields.Char(string='Room Name', related='course_id.room_id.name',readonly=True)
    location_name = fields.Char(string='Location Name', related='course_id.location_id.name',readonly=True)
    total_seats = fields.Integer(string='Total Seats', related='course_id.total_seats',readonly=True)
    
    approval_request_id = fields.Many2one(
        'approval.request',
        string='Approval Request',
        readonly=True,
        copy=False
    )
    
    approval_status = fields.Selection(
        related='approval_request_id.state',
        string='Approval Status',
        readonly=True,
        store=True
    )

    can_current_user_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_can_current_user_approve',
        store=False
    )

    def _compute_can_current_user_approve(self):
        for record in self:
            if record.approval_request_id:
                record.can_current_user_approve = record.approval_request_id.sudo().can_current_user_approve
            else:
                record.can_current_user_approve = False

    @api.model_create_multi
    def create(self, vals):
        employee = self.env.user.employee_id
        if not employee:
            raise ValidationError("Your user account is not linked to an employee record. Please contact HR.")
        for val in vals:
            course = self.env['training.courses'].browse(val['course_id'])
            contract = self.env['hr.version'].sudo().search([
                ('employee_id', '=', employee.id),
                ('contract_date_end', '>=', date.today())
            ], order='contract_date_start asc', limit=1)
            start_of_year = date(date.today().year, 1, 1)
            courses_this_year = self.env['training.registration'].search_count([
                ('trainee_id', '=', employee.id),
                ('create_date', '>=', start_of_year),
                ('approval_status', '=', 'approved')
            ])
            pending_requests = self.env['training.registration'].search_count([
                ('trainee_id', '=', employee.id),
                ('approval_status', 'in', ['waiting', 'in_progress'])
            ])
            if contract and contract.date_start:
                six_months_after_start = contract.date_start + relativedelta(months=6)
                
                if fields.Date.today() < six_months_after_start:
                    raise ValidationError("You must complete 6 months from your contract start date.")
            else:
                raise ValidationError("Contract start date is missing. Please contact HR.")
            if course.available_seats <= 0:
                raise ValidationError("No available seats for this course.")
            if course.deadline and fields.Date.today() > course.deadline:
                raise ValidationError("Registration deadline has passed.")
            if courses_this_year >= 1:
                raise ValidationError("Employee cannot enroll for more than 1 course per year.")
            if pending_requests >= 1:
                raise ValidationError("Employee cant register while having a pending request.")
        
        # Create registration first
        registration = super(TrainingRegistration, self).create(vals)
        
        # Find workflow for training registration
        workflow = self.env['approval.workflow'].sudo().search([
            ('model_name', '=', 'training.registration'),
            ('active', '=', True)
        ], limit=1)
        
        if workflow:
            approval_request = self.env['approval.request'].create({
                'workflow_id': workflow.id,
                'res_model': 'training.registration',
                'res_id': registration.id,
                'requester_id': self.env.user.id,
            })
            registration.approval_request_id = approval_request.id
            registration.message_post(body=_('Training registration created. Click Submit to send for approval.'))
        else:
            registration.message_post(body=_('Warning: No approval workflow configured for training registrations.'))
        
        return registration

    def action_submit(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise ValidationError("No approval request found for this registration.")

        self.approval_request_id.sudo().action_submit()
        self.message_post(body=_('Training registration submitted for approval.'))
    
    def action_open_approve_wizard(self):
        """Open the approve wizard for the approval request"""
        self.ensure_one()
        if not self.approval_request_id:
            raise ValidationError("No approval request found for this registration.")
        return self.approval_request_id.sudo().action_open_approve_wizard()
    
    def action_open_reject_wizard(self):
        """Open the reject wizard for the approval request"""
        self.ensure_one()
        if not self.approval_request_id:
            raise ValidationError("No approval request found for this registration.")
        return self.approval_request_id.sudo().action_open_reject_wizard()

    def _on_approval_completed(self, approved):
        """Called when approval workflow is completed"""
        for record in self:
            if approved:
                # Create training.my.courses record for approved registrations
                self.env['training.my.courses'].create({
                    'registration_id': record.id
                })
                record.message_post(body=_('Training registration approved.'))
            else:
                record.message_post(body=_('Training registration rejected.'))
    
    def unlink(self):
        for record in self:
            if record.approval_status in ['approved', 'rejected']:
                raise ValidationError("You cannot delete an approved or rejected registration record.")
        approval_requests = self.mapped('approval_request_id').filtered(lambda r: r.exists())
        res = super().unlink()
        approval_requests.unlink()
        return res
from datetime import date
from odoo import api, models, fields
from odoo.exceptions import ValidationError
from odoo.tools.convert import relativedelta

class TrainingRegistration(models.Model):
    _name = 'training.registration'
    _description = 'Training Registration'

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
    status = fields.Selection([
        ('approved','Approved'),
        ('rejected','Rejected')
    ])

    @api.model_create_multi
    def create(self, vals):
        employee = self.env.user.employee_id
        if not employee:
            raise ValidationError("Your user account is not linked to an employee record. Please contact HR.")
        for val in vals:
            course = self.env['training.courses'].browse(val['course_id'])
            contract = self.env['hr.version'].search([
                ('employee_id', '=', employee.id),
                ('contract_date_end', '>=', date.today())
            ], order='contract_date_start asc', limit=1)
            start_of_year = date(date.today().year, 1, 1)
            courses_this_year = self.env['training.registration'].search_count([
                ('trainee_id', '=', employee.id),
                ('create_date', '>=', start_of_year),
                ('status', '=', 'approved')
            ])
            pending_requests = self.env['training.registration'].search_count([
                ('trainee_id', '=', employee.id),
                ('status', '=', False)
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
            return super(TrainingRegistration, self).create(vals)
    
    def set_approved(self):
        for record in self:
            if not record.status:
                record.status='approved'
                self.env['training.my.courses'].create({
                'registration_id': record.id
            })
    
    def set_rejected(self):
        for record in self:
            if not record.status:
                record.status='rejected'
    
    def unlink(self):
        for record in self:
            if record.status in ['approved', 'rejected']:
                raise ValidationError("You cannot delete an approved or rejected registration record.")
            return super().unlink()
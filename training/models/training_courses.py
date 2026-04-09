from odoo import api, models, fields
from odoo.exceptions import ValidationError

class TrainingCourses(models.Model):
    _name = 'training.courses'
    _description = 'Training Courses'

    serial_number = fields.Char(string='Serial Number', required=True)
    name = fields.Char(string='Course Name', required=True)
    description = fields.Text(string='Description')
    teacher_id = fields.Many2one(
    'hr.employee', 
    string='Teacher',
    domain="[('job_id.name', '=', 'Teacher')]"
)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    number_of_days = fields.Integer(string='Number of Days', compute='_compute_number_of_days')
    time = fields.Float(string='Time (hours)',default=2.0 , required=True)
    room_id = fields.Many2one('training.rooms', string='Room', required=True)
    location_id = fields.Many2one('training.locations', string='Location', required=True)
    available_seats = fields.Integer(string='Available Seats', compute='_compute_available_seats')
    total_seats = fields.Integer(string='Total Seats',default=15, required=True)
    target_gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Target Gender',)
    deadline = fields.Date(string='Registration Deadline', required=True)
    registration_ids = fields.One2many('training.registration', 'course_id', string='Registrations')
    _unique_serial_number = models.Constraint('UNIQUE(serial_number)','Serial number must be unique!')
    _check_time = models.Constraint('CHECK(time >= 0.30)','Time must be at least 30 min!')
    _check_total_seats = models.Constraint('CHECK(total_seats >= 15)','Total seats must be at least 15!')

    @api.depends("total_seats", "registration_ids")
    def _compute_available_seats(self):
        for course in self:
            taken = len(course.registration_ids)
            course.available_seats = course.total_seats - taken

    @api.depends('start_date', 'end_date')
    def _compute_number_of_days(self):
        for course in self:
            if course.start_date and course.end_date:
                delta = course.end_date - course.start_date
                course.number_of_days = delta.days + 1
            else:
                course.number_of_days = 0
    @api.constrains('start_date', 'end_date','deadline')
    def _check_dates(self):
        today = fields.Date.today()
        for record in self:
            if record.start_date and record.start_date <= today:
                raise ValidationError(("The start date must be after today's date."))
            
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError(("The end date must be later than the start date."))
            if record.deadline:
                if record.deadline <= today:
                    raise ValidationError(("The deadline must be later than today."))
                if record.deadline >= record.start_date:
                    raise ValidationError(("The deadline must be before start date."))


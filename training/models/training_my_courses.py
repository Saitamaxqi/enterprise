from odoo import models, fields

class TrainingMyCourses(models.Model):
    _name = 'training.my.courses'
    _description = 'My Training Courses'
    
    registration_id = fields.Many2one('training.registration')
    trainee_id = fields.Many2one(related="registration_id.trainee_id")
    course_serial_number = fields.Char(related="registration_id.course_serial_number")
    course_name = fields.Char(related="registration_id.course_name")
    status = fields.Selection(related="registration_id.status")

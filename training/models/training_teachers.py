from odoo import models, fields

class TrainingTeachers(models.Model):
    _name = 'training.teachers'
    _description = 'Training Teachers'

    name = fields.Char(string='Teacher Name', required=True)
    code = fields.Char(string='Teacher Code', required=True)
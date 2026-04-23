from odoo import models, fields

class TrainingLocations(models.Model):
    _name = 'training.locations'
    _description = 'Training Locations'

    name = fields.Char(string='Location Name', required=True)
    code = fields.Char(string='Location Code', required=True)

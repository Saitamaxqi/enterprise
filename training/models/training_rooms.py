from odoo import models, fields

class TrainingRooms(models.Model):
    _name = 'training.rooms'
    _description = 'Training Rooms'

    name = fields.Char(string='Room Name', required=True)
    code = fields.Char(string='Room Code', required=True)

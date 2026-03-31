from odoo import models, fields

class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'

    res_model
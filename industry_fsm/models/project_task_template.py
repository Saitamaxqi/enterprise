from odoo import models, fields


class ProjectTaskTemplate(models.Model):
    _inherit = "project.task.template"

    is_fsm = fields.Boolean(related='project_id.is_fsm')

from odoo import models, fields


class ProjectTaskTemplate(models.Model):
    _inherit = "project.task.template"

    planned_date_begin = fields.Datetime("Start date")

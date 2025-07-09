# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTaskTemplate(models.Model):
    _inherit = "project.task.template"

    under_warranty = fields.Boolean('Under Warranty',
        help='If ticked, the time and materials used for this task will not be billed to the customer. '
            'However, the inventory of consumed materials will still be updated.')

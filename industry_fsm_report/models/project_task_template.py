from odoo import api, fields, models


class ProjectTaskTemplate(models.Model):
    _inherit = "project.task.template"

    allow_worksheets = fields.Boolean(related='project_id.allow_worksheets')
    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        compute='_compute_worksheet_template_id', store=True, readonly=False,
        domain="[('res_model', '=', 'project.task'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Create templates for each type of intervention you have and customize their content with your own custom fields.")

    @api.depends('project_id')
    def _compute_worksheet_template_id(self):
        # Change worksheet when the project changes, not project.allow_worksheet
        for task_template in self:
            if not task_template.worksheet_template_id and task_template.allow_worksheets:
                task_template.worksheet_template_id = task_template.parent_id.worksheet_template_id.id\
                    if task_template.parent_id else task_template.project_id.worksheet_template_id.id

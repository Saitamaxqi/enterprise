from odoo import api, models
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _view_esg_project_tasks(self):
        project = self.env.ref('esg_project.esg_project_project_0')
        action = project.action_view_tasks()
        domain = action['domain']
        if domain:
            domain = domain.replace('active_id', str(project.id))
        else:
            domain = [('project_id', '=', project.id)]
        action['domain'] = domain
        return action

    @api.ondelete(at_uninstall=False)
    def _prevent_esg_project_deletion(self):
        if self.env.ref('esg_project.esg_project_project_0') in self:
            raise ValidationError(self.env._('You cannot delete the ESG Project.'))
        return super().unlink()

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class PlanningPreview(models.TransientModel):
    _name = 'planning.preview'
    _description = 'Planning Preview'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]"
    )
    slot_count = fields.Integer(compute="_compute_slot_count")

    def _get_datetimes(self):
        start_str = self.env.context.get('default_start_datetime')
        end_str = self.env.context.get('default_end_datetime')

        if not start_str or not end_str:
            raise ValidationError(self.env._("Missing start or end datetime in context."))
        return start_str, end_str

    @api.depends('employee_id')
    def _compute_slot_count(self):
        for record in self:
            if not record.employee_id:
                record.slot_count = 0
                continue

            start_str, end_str = record._get_datetimes()
            employee = record.employee_id
            planning_roles = employee.planning_role_ids
            open_shift_domain = Domain([
                ('employee_id', '=', False),
                ('end_datetime', '<', fields.Datetime.now()),
            ])
            role_domain = Domain([('role_id', '=', False)])
            if planning_roles:
                role_domain |= Domain('role_id', 'in', planning_roles.ids)
            open_shift_domain &= role_domain
            request_to_switch_domain = Domain('request_to_switch', '=', True) & role_domain
            domain = Domain([
                ('state', '=', 'published'),
                ('start_datetime', '>', start_str),
                ('end_datetime', '<', end_str),
            ])
            domain &= Domain('employee_id', '=', employee.id) | open_shift_domain | request_to_switch_domain
            record.slot_count = self.env['planning.slot'].search_count(domain)

    def action_preview_shift(self):
        self.ensure_one()
        default_start_str, default_end_str = self._get_datetimes()

        default_start = fields.Datetime.to_datetime(default_start_str)
        default_end = fields.Datetime.to_datetime(default_end_str)
        planning = self.env['planning.planning']._get_preview_planning(default_start, default_end, True)
        planning.is_planning_preview = True
        planning_url = '/planning/%s/%s' % (planning.access_token, self.employee_id.employee_token)

        return {
            'type': 'ir.actions.act_url',
            'url': planning_url,
            'target': 'new',
        }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_show_contract_reviews(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.version",
            "views": [[False, "list"], [False, "form"]],
            "domain": [["origin_version_id", "=", self.version_id.id]],
            "name": "Contracts Reviews",
        }

    def action_show_offers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_contract_salary.hr_contract_salary_offer_action')
        action['domain'] = [('id', 'in', self.salary_offer_ids.ids)]
        action['context'] = {'default_employee_version_id': self.id}
        if self.salary_offers_count == 1:
            action.update({
                "views": [[False, "form"]],
                "res_id": self.salary_offer_ids.id,
            })
        return action

    def action_generate_offer(self):

        offer_validity_period = int(self.env['ir.config_parameter'].sudo().get_param(
            'hr_contract_salary.employee_salary_simulator_link_validity', default=30))
        offer_values = self._get_offer_values()
        offer_values['validity_days_count'] = offer_validity_period
        offer = self.env['hr.contract.salary.offer'].with_context(
            default_contract_template_id=self.version_id).create(offer_values)

        self.message_post(
            body=_("An %(offer)s has been sent by %(user)s to the employee (mail: %(email)s)",
                    offer=Markup("<a href='#' data-oe-model='hr.contract.salary.offer' data-oe-id='{offer_id}'>Offer</a>")
                    .format(offer_id=offer.id),
                    user=self.env.user.name,
                    email=self.work_email
            )
        )

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.contract.salary.offer',
            'res_id': offer.id,
            'views': [(False, 'form')],
            'context': {'active_model': 'hr.version', 'default_employee_version_id': self.version_id.id}
        }

    def _get_offer_values(self):
        self.ensure_one()
        return {
            'company_id': self.company_id.id,
            'contract_template_id': self.version_id.id,
            'employee_version_id': self.version_id.id,
            'final_yearly_costs': self.final_yearly_costs,
            'job_title': self.job_id.name,
            'employee_job_id':  self.job_id.id,
            'department_id': self.department_id.id,
        }

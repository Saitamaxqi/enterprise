from odoo import models, _
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment
from odoo.osv.expression import AND


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    def _get_hardcoded_sample(self, model):
        if model._name != 'appointment.type':
            return super()._get_hardcoded_sample(model)

        return [{
            'message_intro': _("A first step in joining our team as a technical consultant."),
            'name': _('Candidate Interview'),
        }, {
            'name': _('Online Cooking Lesson'),
        }, {
            'name': _('Tennis Court'),
        }]

    def _prepare_values(self, limit=None, search_domain=None):
        if self.model_name == 'appointment.type':
            if country := WebsiteAppointment._get_customer_country():
                customer_country_domain = [('country_ids', 'in', [False, country.id])]
                search_domain = AND([search_domain, customer_country_domain])
        return super()._prepare_values(limit=limit, search_domain=search_domain)

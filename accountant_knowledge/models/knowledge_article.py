import json
from lxml import html
from odoo import api, fields, models
from odoo.fields import Domain


class KnowledgeArticle(models.Model):
    _name = 'knowledge.article'
    _inherit = ['knowledge.article']

    audit_report_id = fields.One2many('audit.report', 'knowledge_article_id')
    inherited_audit_report_id = fields.One2many('audit.report',
        compute='_compute_inherited_audit_report', store=False)
    is_audit_report_template = fields.Boolean('Audit Report Template')

    @api.depends('audit_report_id')
    def _compute_inherited_audit_report(self):
        for article in self:
            current = article
            while current and not current.audit_report_id:
                current = current.parent_id
            article.inherited_audit_report_id = current.audit_report_id \
                if current and current.audit_report_id else False

    def update_embedded_audit_report_options(self, html_element_host_id, new_options):
        self.ensure_one()
        fragment = html.fragment_fromstring(self.body, create_parent=True)
        selector = f'.//*[@data-embedded="accountReport"][@data-oe-id="{html_element_host_id}"]'
        for element in fragment.findall(selector):
            element.set('data-embedded-props', json.dumps({
                **json.loads(element.get('data-embedded-props')),
                'options': new_options
            }))
        elements = []
        for child in fragment.getchildren():
            elements.append(
                html.tostring(child, encoding='unicode', method='html'))
        self.write({
            'body': ''.join(elements)
        })

    @api.model
    def _get_available_template_domain(self):
        base_domain = super()._get_available_template_domain()
        return Domain.AND([base_domain, [("is_audit_report_template", "=", False)]])

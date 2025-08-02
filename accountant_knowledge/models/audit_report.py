import ast
import re
import json

from datetime import datetime
from lxml import html

from odoo import _, api, Command, fields, models


class AuditReport(models.Model):
    _name = 'audit.report'
    _description = 'Audit Report'

    knowledge_article_id = fields.Many2one(
        'knowledge.article', string='Article', required=True, index=True)

    color = fields.Integer(string='Color Index', export_string_translation=False)
    title = fields.Char(string='Title', required=True, translate=True)
    status = fields.Selection(string='Status',
        selection=[('draft', 'Draft'), ('done', 'Done')], default='draft')
    start_date = fields.Date(string='Start Date', required=True,
        help='Start Date, included in the fiscal year.',
        default=lambda self: datetime(year=datetime.now().year - 1, month=1, day=1))
    end_date = fields.Date(string='End Date', required=True,
        help='Ending Date, included in the fiscal year.',
        default=lambda self: datetime(year=datetime.now().year - 1, month=12, day=31))
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    responsible_user_ids = fields.Many2many('res.users', string='Responsibles',
        default=lambda self: self.env.user)
    knowledge_template_article_id = fields.Many2one(
        'knowledge.article', string='Audit Report Template', required=True,
        domain="[('is_audit_report_template', '=', True)]",
        default=lambda self: self.env['knowledge.article'].search([('is_audit_report_template', '=', True)], limit=1))

    @api.model_create_multi
    def create(self, vals_list):
        root_articles = self.env['knowledge.article'].create([{
            'internal_permission': 'none',
            'article_member_ids': [(0, 0, {
                'partner_id': self.env.user.partner_id.id,
                'permission': 'write'
            })]
        } for _ in vals_list])
        for vals, root_article in zip(vals_list, root_articles):
            vals['knowledge_article_id'] = root_article.id

        audit_reports = super().create(vals_list)
        for audit_report, root_article in zip(audit_reports, root_articles):

            template_to_article_pairs = []
            stack = [(audit_report.knowledge_template_article_id, root_article)]

            while stack:
                (parent_template, parent_article) = stack.pop()
                template_to_article_pairs.append((parent_template, parent_article))

                # Create the child articles:
                child_templates = parent_template.child_ids
                child_templates = child_templates.filtered(
                    lambda template: template.template_child_default_create)
                child_templates = child_templates.sorted(
                    lambda template: (template.write_date, template.id))

                if not child_templates:
                    continue

                child_articles_values = []
                for template in child_templates:
                    child_articles_values.append({
                        'is_article_item': template.is_article_item,
                        'parent_id': parent_article.id,
                        'icon': template.icon,
                        'name': template.template_name,
                    })

                child_articles = self.env['knowledge.article'].create(child_articles_values)
                stack.extend(zip(child_templates, child_articles))

            template_xml_id_to_article_id_mapping = {}
            all_ir_model_data = self.env['ir.model.data'].sudo().search([
                ('model', '=', 'knowledge.article'),
                ('res_id', 'in', [template.id for (template, _) in template_to_article_pairs])
            ])

            for (template, article) in template_to_article_pairs:
                ir_model_data = all_ir_model_data.filtered(
                    lambda ir_model_data: ir_model_data.res_id == template.id)
                if ir_model_data:
                    template_xml_id = ir_model_data.complete_name
                    template_xml_id_to_article_id_mapping[template_xml_id] = article.id

            def ref(xml_id):
                return template_xml_id_to_article_id_mapping[xml_id] \
                    if xml_id in template_xml_id_to_article_id_mapping \
                        else self.env.ref(xml_id).id

            def transform_xmlid_to_res_id(match):
                return str(ref(match.group('xml_id')))

            for (template, article) in reversed(template_to_article_pairs):
                fragment = html.fragment_fromstring(template.template_body, create_parent='div')

                for element in fragment.xpath('//*[@data-embedded="articleIndex"]'):
                    element.set('data-embedded-props', json.dumps({
                        'articles': [{
                            'id': child.id,
                            'name': child.display_name,
                            'childIds': []
                        } for child in article.child_ids],
                    }))

                for element in fragment.xpath('//*[@data-embedded="accountReport"]'):
                    embedded_props = ast.literal_eval(re.sub(
                        r'(?<![\w])ref\(\'(?P<xml_id>\w+\.\w+)\'\)',
                        transform_xmlid_to_res_id,
                        element.get('data-embedded-props')))
                    if 'options' in embedded_props:
                        account_report_options = embedded_props['options']
                        if 'report_id' in account_report_options:
                            account_report = self.env['account.report'].browse(account_report_options['report_id'])
                            embedded_props['options'] = account_report.get_options({
                                'selected_variant_id': account_report.id,
                                'date': {
                                    'date_from': str(audit_report.start_date),
                                    'date_to': str(audit_report.end_date),
                                    'mode': 'range',
                                    'filter': 'custom',
                                },
                            })
                    element.set('data-embedded-props', json.dumps(embedded_props))

                elements = []
                for child in fragment.getchildren():
                    elements.append(
                        html.tostring(child, encoding='unicode', method='html'))

                article.write({
                    'article_properties': template.article_properties or {},
                    'article_properties_definition': template.article_properties_definition,
                    'body': ''.join(elements),
                    'cover_image_id': template.cover_image_id.id,
                    'full_width': template.full_width,
                    'icon': template.icon,
                    'name': template.template_name,
                    'origin_template_id': template.id,
                })

            # Invite the responsible users:
            for user in audit_report.responsible_user_ids:
                root_article.invite_members(user.mapped('partner_id'), 'write')
        return audit_reports

    def write(self, vals):
        if vals.get('responsible_user_ids'):
            user_ids = [command[1] for command in vals['responsible_user_ids'] if command[0] == Command.LINK]
            users = self.env['res.users'].browse(user_ids)
            for article in self.knowledge_article_id:
                article.invite_members(users.mapped('partner_id'), 'write')
        return super().write(vals)

    def action_set_to_draft(self):
        self.status = 'draft'

    def action_set_to_done(self):
        self.status = 'done'

    def action_edit_audit_report(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'accountant_knowledge.action_audit_report_quick_create')
        action['name'] = _('Edit Audit Report')
        action['res_id'] = self.id
        return action

    def action_audit_report_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/knowledge_accountant/article/{self.knowledge_article_id.id}/audit_report?include_pdf_files=true&include_child_articles=true',
            'target': 'download'
        }

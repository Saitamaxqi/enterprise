from odoo import models, osv


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_audit_line_domain(self, column_group_options, expression, params):
        res = super()._get_audit_line_domain(column_group_options, expression, params)
        if expression.formula == '_report_custom_engine_total_disallowed_expenses':
            res = osv.expression.AND([res, [('account_id.disallowed_expenses_category_id.id', '!=', False)]])
        return res

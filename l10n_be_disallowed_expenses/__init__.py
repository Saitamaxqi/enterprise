# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def _l10n_be_disallowed_expenses_post_init(env):
    for company in env['res.company'].search([('chart_template', 'in', ('be_comp', 'be_asso')), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        Template._load_data({
            'account.account': Template._get_be_disallowed_expenses_accounts(),
        })

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '!=', False), ('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({
            'account.asset': ChartTemplate._get_account_asset(company.chart_template),
            'account.account': {
                xmlid: filtered_vals
                for xmlid, vals in ChartTemplate._get_account_account(company.chart_template).items()
                if (filtered_vals := {
                    fname: value
                    for fname, value in vals.items()
                    if fname in ['create_asset', 'asset_model_ids']
                })
            }
        })

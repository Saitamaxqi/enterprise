# Part of Odoo. See LICENSE file for full copyright and licensing details.

def post_init_hook(env):
    # The `l10n_pe_edi_affectation_reason` field on `account.move.line` is created manually
    # to prevent "out of memory" (OOM) errors during module installation.
    # The field is populated here to ensure the values are filled after the related field
    # on `account.tax` has been computed.
    env.cr.execute("""
        UPDATE account_move_line aml
        SET l10n_pe_edi_affectation_reason = (
            SELECT at.l10n_pe_edi_affectation_reason
            FROM account_move_line_account_tax_rel rel
            JOIN account_tax at ON at.id = rel.account_tax_id
            WHERE rel.account_move_line_id = aml.id
            AND at.l10n_pe_edi_tax_code IS NOT NULL
            ORDER BY at.id
            LIMIT 1
        )
        WHERE aml.display_type NOT IN ('tax', 'payment_term')
        AND EXISTS (
            SELECT 1
            FROM account_move_line_account_tax_rel rel
            JOIN account_tax at ON at.id = rel.account_tax_id
            WHERE rel.account_move_line_id = aml.id
            AND at.l10n_pe_edi_tax_code IS NOT NULL
        );
    """)

    for company in env['res.company'].search([('chart_template', '=', 'pe'), ('parent_id', '=', False)]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        tax_group_data = ChartTemplate._get_pe_edi_account_tax_group()
        ChartTemplate._load_data({'account.tax.group': tax_group_data})

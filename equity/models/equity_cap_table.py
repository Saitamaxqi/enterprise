from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class EquityCapTable(models.Model):
    _name = 'equity.cap.table'
    _description = "Cap Table"
    _auto = False

    partner_id = fields.Many2one('res.partner')
    holder_id = fields.Many2one('res.partner')
    share_class_id = fields.Many2one('equity.share.class')

    shares = fields.Float()
    options = fields.Float()
    votes = fields.Float()

    ownership = fields.Float()
    voting_rights = fields.Float()
    shares_dilution = fields.Float()
    options_dilution = fields.Float()
    shares_valuation = fields.Float()
    options_valuation = fields.Float()

    @property
    def _table_query(self):
        self.env['equity.transaction'].flush_model()
        current_date = self.env.context.get('current_date') or fields.Date.context_today(self)
        domain = Domain('date', '<=', current_date)
        if current_transaction_id := self.env.context.get('current_transaction_id'):
            domain &= Domain('id', '!=', current_transaction_id)
        options_query = self.env['equity.transaction']._search(domain & Domain('transaction_type', '=', 'option'))
        share_query = self.env['equity.transaction']._search(domain & Domain('transaction_type', '=', 'share'))
        sale_query = self.env['equity.transaction']._search(domain & Domain('transaction_type', '=', 'sale'))
        common_cols = [
            'partner_id',
            'share_class_id',
        ]
        all_transactions = SQL(" UNION ALL ").join([
            options_query.select(
                *common_cols,
                'subscriber_id AS holder_id',
                '0 AS shares',
                SQL('securities - CASE WHEN expiration_date <= %s THEN remaining_options ELSE 0 END AS options', current_date),
            ),
            share_query.select(
                *common_cols,
                'subscriber_id AS holder_id',
                'securities AS shares',
                'CASE WHEN parent_transaction_id IS NULL THEN 0 ELSE -securities END AS options',
            ),
            sale_query.select(
                *common_cols,
                'subscriber_id AS holder_id',
                'securities AS shares',
                '0 AS options',
            ),
            sale_query.select(
                *common_cols,
                'seller_id AS holder_id',
                '-securities AS shares',
                '0 AS options',
            ),
        ])
        return SQL(
            """
                WITH transactions AS (%(all_transactions)s)
              SELECT CONCAT(partner_id, '-', holder_id, '-', share_class_id, '-', %(current_date)s) AS id,
                     partner_id,
                     holder_id,
                     share_class_id,
                     SUM(shares) AS shares,
                     SUM(options) AS options,
                     SUM(shares * share_class.share_votes) AS votes,
                     SUM(shares) / NULLIF(SUM(SUM(shares)) OVER by_partner, 0) AS ownership,
                     SUM(shares * share_class.share_votes) / NULLIF(SUM(SUM(shares * share_class.share_votes)) OVER by_partner, 0) AS voting_rights,
                     SUM(shares) / NULLIF(SUM(SUM(shares + options)) OVER by_partner, 0) AS shares_dilution,
                     SUM(options) / NULLIF(SUM(SUM(shares + options)) OVER by_partner, 0) AS options_dilution,
                     SUM(shares) / NULLIF((SUM(SUM(shares + options)) OVER by_partner), 0) * last_valuation.valuation AS shares_valuation,
                     SUM(options) / NULLIF((SUM(SUM(shares + options)) OVER by_partner), 0) * last_valuation.valuation AS options_valuation
                FROM transactions
                JOIN equity_share_class share_class ON share_class.id = transactions.share_class_id
   LEFT JOIN LATERAL (
                        SELECT valuation
                          FROM equity_valuation
                         WHERE partner_id = transactions.partner_id
                           AND date <= %(current_date)s
                      ORDER BY date DESC
                         LIMIT 1
                     ) last_valuation ON TRUE
            GROUP BY partner_id, holder_id, share_class_id, last_valuation.valuation
              WINDOW by_partner AS (PARTITION BY partner_id)
            """,
            all_transactions=all_transactions,
            current_date=current_date,
        )

    def _append_cap_table_entry(self, data, cap_table_entry):
        share_class_id = cap_table_entry.share_class_id.id
        data['classes'][share_class_id]['shares'] += cap_table_entry.shares
        data['classes'][share_class_id]['options'] += cap_table_entry.options

        data['ownership'] += cap_table_entry.ownership
        data['voting_rights'] += cap_table_entry.voting_rights
        data['dilution']['shares'] += cap_table_entry.shares_dilution
        data['dilution']['options'] += cap_table_entry.options_dilution
        data['valuation']['shares'] += cap_table_entry.shares_valuation
        data['valuation']['options'] += cap_table_entry.options_valuation
        return data

    @api.model
    def get_cap_table_data(self, partner_ids):
        # {partner_id: {holder_id: {...}}}
        partner_holder_data = defaultdict(lambda: defaultdict(lambda: {
            'classes': defaultdict(lambda: {'shares': 0, 'options': 0}),
            'ownership': 0,
            'voting_rights': 0,
            'dilution': {'shares': 0, 'options': 0},
            'valuation': {'shares': 0, 'options': 0},
        }))
        partner_classes_ids = defaultdict(list)
        partner_data = {}
        class_data = {}

        domain = []
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))

        for cap_table_entry in self.search(domain):
            partner = cap_table_entry.partner_id
            holder = cap_table_entry.holder_id
            share_class = cap_table_entry.share_class_id

            if partner.id not in partner_data:
                partner_data[partner.id] = partner._get_cap_table_data()
            if holder and holder.id not in partner_data:
                partner_data[holder.id] = holder._get_cap_table_data()

            if share_class.id not in class_data:
                class_data[share_class.id] = share_class._get_cap_table_data()

            if share_class.id not in partner_classes_ids[partner.id]:
                partner_classes_ids[partner.id].append(share_class.id)

            self._append_cap_table_entry(partner_holder_data[partner.id][holder.id], cap_table_entry)

        for partner_id, share_class_ids in partner_classes_ids.items():
            partner_classes_ids[partner_id] = self.env['equity.share.class'].browse(share_class_ids).sorted().ids

        return {
            'partner_holder_data': partner_holder_data,
            'partner_classes_ids': partner_classes_ids,
            'partner_data': partner_data,
            'class_data': class_data,
        }

    @api.model
    @api.readonly
    def search(self, domain, offset: int = 0, limit: int | None = None, order: str | None = None):
        # Always fetch all the fields when searching to avoid doing a lookup by id afterwards
        return self.search_fetch(domain, list(self._fields), offset=offset, limit=limit, order=order)

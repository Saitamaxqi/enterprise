from odoo import api, models, fields
from odoo.tools.float_utils import float_repr


class EquityShareClass(models.Model):
    _name = 'equity.share.class'
    _description = "Share Class"
    _order = 'sequence ASC, name ASC, id ASC'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10, required=True)
    share_votes = fields.Integer(string="Votes per Share", required=True, default=1)
    dividend_payout = fields.Boolean(default=True)

    @api.depends('name')
    @api.depends_context('transaction_id', 'transaction_type', 'transaction_date', 'partner_id', 'subscriber_id', 'seller_id', 'formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get('formatted_display_name'):
            return
        securities_per_class = self._get_securities_per_class()
        for share_class in self:
            if (remaining := securities_per_class.get(share_class)) is not None:
                share_class.display_name += f" --{float_repr(remaining, 2)}--"

    def _get_securities_per_class(self):
        transaction_id = self.env.context.get('transaction_id')
        transaction_type = self.env.context.get('transaction_type')
        transaction_date = self.env.context.get('transaction_date')
        partner_id = self.env.context.get('partner_id')
        subscriber_id = self.env.context.get('subscriber_id')
        seller_id = self.env.context.get('seller_id')

        holder_id = None
        if transaction_type == 'sale':
            holder_id = seller_id
        else:
            holder_id = subscriber_id

        if (
            not transaction_type
            or transaction_type == 'exercise'
            or not transaction_date
            or not partner_id
            or not holder_id
        ):
            return {}

        securities_per_class = self.env['equity.cap.table'].with_context(
            current_date=transaction_date,
            current_transaction_id=transaction_id,
        )._read_group(
            domain=[
                ('partner_id', '=', partner_id),
                ('holder_id', '=', holder_id),
                ('share_class_id', '=', self.id),
            ],
            groupby=['share_class_id'],
            aggregates=['shares:sum', 'options:sum'],
        )

        securities_per_class = {
            share_class: options if transaction_type == 'option' else shares
            for share_class, shares, options in securities_per_class
        }

        return {
            share_class: securities_per_class.get(share_class) or 0
            for share_class in self
        }

    def _get_cap_table_data(self):
        self.ensure_one()
        return {
            'display_name': self.display_name,
        }

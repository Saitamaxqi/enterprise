from dateutil.relativedelta import relativedelta

from odoo import api, models, fields
from odoo.exceptions import ValidationError


class EquityTransaction(models.Model):
    _name = 'equity.transaction'
    _inherit = ['mail.thread']
    _description = 'Equity Transaction'

    transaction_type = fields.Selection(
        string="Transaction Type",
        selection=[
            ('share', "Shares Issuance"),
            ('option', "Options Issuance"),
            ('sale', "Sale"),
        ],
        default='share',
        required=True,
    )
    remaining_options = fields.Float(
        compute='_compute_remaining_options', store=True,
        help="Number of options not exercised",
    )
    parent_transaction_id = fields.Many2one('equity.transaction', index='btree_not_null')
    child_transaction_ids = fields.One2many('equity.transaction', 'parent_transaction_id')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Company",
        default=lambda self: self.env.company.partner_id,
        domain=[('is_company', '=', True)],
        required=True,
        index='btree',
    )
    equity_currency_id = fields.Many2one(comodel_name='res.currency', string="Currency", related='partner_id.equity_currency_id')
    date = fields.Date(default=fields.Date.context_today, required=True)
    expiration_date = fields.Date(
        string="Expiration",
        compute='_compute_expiration_date', store=True, readonly=False,
        tracking=True,
    )
    expiration_diff = fields.Text(compute='_compute_expiration_diff')
    securities = fields.Float(
        string="# Securities",
        required=True,
        tracking=True,
        help="Negative amount is a destruction.",
    )
    share_class_id = fields.Many2one(comodel_name='equity.share.class', string="Class", required=True)
    invalid_securities_error = fields.Text(compute='_compute_invalid_securities_error')
    security_price = fields.Monetary(
        string="Price per Security",
        currency_field='equity_currency_id',
        compute='_compute_security_price', store=True, readonly=False,
        tracking=True,
    )
    transfer_amount = fields.Monetary(string="Transfer Amount", currency_field='equity_currency_id', compute='_compute_transfer_amount')
    notes = fields.Text()

    seller_id = fields.Many2one(comodel_name='res.partner', string="Seller", tracking=True, compute='_compute_seller_id', store=True, readonly=False)
    subscriber_id = fields.Many2one(
        comodel_name='res.partner',
        string="Subscriber",
        tracking=True,
        help="Recipient of the shares/options of the transaction.",
    )
    subscriber_id_placeholder = fields.Char(compute='_compute_subscriber_id_placeholder')

    attachment_ids = fields.One2many(comodel_name='ir.attachment', inverse_name='res_id', string="Attachments")
    attachment_number = fields.Integer(compute='_compute_attachment_number')

    @api.constrains('seller_id', 'subscriber_id')
    def _check_seller_not_subscriber(self):
        for record in self:
            if record.seller_id and record.subscriber_id and record.seller_id.id == record.subscriber_id.id:
                raise ValidationError(self.env._("Seller and Buyer must be different."))

    @api.constrains('partner_id', 'transaction_type', 'subscriber_id', 'seller_id', 'share_class_id', 'securities')
    def _check_invalid_securities_error(self):
        for record in self:
            if record.invalid_securities_error:
                raise ValidationError(record.invalid_securities_error)

    @api.constrains('transaction_type', 'expiration_date', 'date')
    def _check_expiration_date(self):
        for record in self.filtered(lambda t: t.transaction_type == 'option'):
            if record.expiration_date < record.date:
                raise ValidationError(self.env._("Expiration date must be after the transaction date"))

    @api.constrains('transaction_type', 'parent_transaction_id', 'date', 'partner_id', 'subscriber_id', 'share_class_id', 'security_price')
    def _check_options_exercise_transaction(self):
        for record in self.filtered(lambda t: t.parent_transaction_id):
            parent = record.parent_transaction_id
            if record.transaction_type != 'share':
                raise ValidationError(self.env._("Cannot change type of exercise transaction"))
            if record.date > parent.expiration_date:
                raise ValidationError(self.env._("Cannot exercise options after their expiry date"))
            if record.date < parent.date:
                raise ValidationError(self.env._("Cannot exercise options before their issuance date"))
            if record.partner_id != parent.partner_id:
                raise ValidationError(self.env._("Exercised options must have the same Company as the original options"))
            if record.subscriber_id != parent.subscriber_id:
                raise ValidationError(self.env._("Exercised options must have the same Subscriber as the original options"))
            if record.share_class_id != parent.share_class_id:
                raise ValidationError(self.env._("Exercised options must have the same Share Class as the original options"))
            if record.security_price != parent.security_price:
                raise ValidationError(self.env._("Exercised options must have the same Security Price as the original options"))

    @api.constrains('transaction_type', 'child_transaction_ids', 'expiration_date', 'partner_id', 'subscriber_id', 'share_class_id', 'security_price', 'securities')
    def _check_options_issuance_transaction(self):
        for record in self.filtered(lambda t: t.child_transaction_ids):
            children = record.child_transaction_ids
            if record.transaction_type != 'option':
                raise ValidationError(self.env._("Cannot change transaction type because it has exercised options"))
            if record.expiration_date < max(children.mapped('date')):
                raise ValidationError(self.env._("Expiry date cannot precede exercise dates"))
            if record.date > min(children.mapped('date')):
                raise ValidationError(self.env._("Date cannot succeed exercise dates"))
            if record.partner_id != children[0].partner_id:
                raise ValidationError(self.env._("Options must have the same Company as exercised options"))
            if record.subscriber_id != children[0].subscriber_id:
                raise ValidationError(self.env._("Options must have the same Subscriber as exercised options"))
            if record.share_class_id != children[0].share_class_id:
                raise ValidationError(self.env._("Options must have the same Share Class as exercised options"))
            if record.security_price != children[0].security_price:
                raise ValidationError(self.env._("Options must have the same Security Price as exercised options"))
            if record.securities < sum(children.mapped('securities')):
                raise ValidationError(self.env._("More options have already been exercised"))

    @api.depends('securities', 'transaction_type', 'child_transaction_ids.securities')
    def _compute_remaining_options(self):
        for transaction in self:
            if transaction.transaction_type != 'option':
                transaction.remaining_options = 0
            else:
                transaction.remaining_options = transaction.securities - sum(transaction.child_transaction_ids.mapped('securities'))

    @api.depends('date')
    def _compute_expiration_date(self):
        for transaction in self.filtered(lambda t: t.date):
            transaction.expiration_date = transaction.date.replace(year=transaction.date.year + 3)

    @api.depends('transaction_type', 'securities', 'expiration_date')
    def _compute_expiration_diff(self):
        def diff_text(diff_val, singular_diff_type, plural_diff_type):
            diff_type = plural_diff_type if diff_val != 1 else singular_diff_type
            return f"({diff_val} {diff_type})"

        self.expiration_diff = False
        for transaction in self.filtered(lambda t: t.transaction_type == 'option'):
            if transaction.securities <= 0:
                transaction.expiration_diff = self.env._("(Non-positive options don't expire)")
                continue

            today = fields.Date.today()
            if transaction.expiration_date and transaction.expiration_date >= today:
                diff = relativedelta(transaction.expiration_date, today)
                if diff.years >= 1:
                    transaction.expiration_diff = diff_text(diff.years, self.env._("year"), self.env._("years"))
                elif diff.months >= 1:
                    transaction.expiration_diff = diff_text(diff.months, self.env._("month"), self.env._("months"))
                else:
                    transaction.expiration_diff = diff_text(diff.days, self.env._("day"), self.env._("days"))
            elif transaction.expiration_date:
                transaction.expiration_diff = self.env._("(expired)")
            else:
                transaction.expiration_diff = ""

    @api.depends('partner_id', 'transaction_type', 'parent_transaction_id.remaining_options', 'subscriber_id', 'seller_id', 'share_class_id', 'securities')
    def _compute_invalid_securities_error(self):
        self.invalid_securities_error = False
        for transaction in self.filtered(lambda t: t.partner_id and t.share_class_id):
            if transaction.securities == 0:
                transaction.invalid_securities_error = self.env._("Securities cannot be zero")
                continue

            cap_table_entries = self.env['equity.cap.table'].with_context(current_date=transaction.date).search([
                ('partner_id', '=', transaction.partner_id.id),
                ('holder_id', 'in', (transaction.subscriber_id | transaction.seller_id).ids),
                ('share_class_id', '=', transaction.share_class_id.id),
            ])

            subscriber_shares = sum(cap_table_entries.filtered(lambda cte: cte.holder_id == transaction.subscriber_id).mapped('shares'))
            seller_shares = sum(cap_table_entries.filtered(lambda cte: cte.holder_id == transaction.seller_id).mapped('shares'))
            if (
                transaction.transaction_type == 'share'
                and not transaction.parent_transaction_id
                and transaction.securities < 0
                and subscriber_shares < 0
            ):
                transaction.invalid_securities_error = self.env._(
                    "Only %(subscriber_shares)s %(share_class_name)s shares available for destruction",
                    subscriber_shares=subscriber_shares - transaction.securities,
                    share_class_name=transaction.share_class_id.name,
                )
            elif transaction.transaction_type == 'share' and transaction.parent_transaction_id:
                if transaction.securities < 0:
                    transaction.invalid_securities_error = self.env._("Cannot exercise negative options")
                elif transaction.parent_transaction_id.remaining_options < 0:
                    remaining_options = transaction.parent_transaction_id.remaining_options + transaction.securities
                    transaction.invalid_securities_error = self.env._(
                        "Only %(remaining_options)s %(share_class_name)s options available for exercise",
                        remaining_options=remaining_options,
                        share_class_name=transaction.share_class_id.name,
                    )
            elif (
                transaction.transaction_type == 'option'
                and transaction.securities < 0
            ):
                transaction.invalid_securities_error = self.env._("Options issued can not be destroyed")
            elif transaction.transaction_type == 'sale':
                if transaction.securities < 0:
                    transaction.invalid_securities_error = self.env._("Cannot sell negative shares")
                elif seller_shares < 0:
                    transaction.invalid_securities_error = self.env._(
                        "Only %(seller_shares)s %(share_class_name)s shares available for sale",
                        seller_shares=seller_shares + transaction.securities,
                        share_class_name=transaction.share_class_id.name,
                    )

    @api.depends('date', 'partner_id', 'parent_transaction_id')
    def _compute_security_price(self):
        for transaction in self.filtered(lambda t: not bool(self._origin.id)):  # only set security price for newly created records
            transaction.security_price = transaction.parent_transaction_id.security_price or self.search([
                ('partner_id', '=', transaction.partner_id.id),
                ('date', '<', transaction.date),
            ], order='date DESC', limit=1).security_price

    @api.depends('securities', 'security_price')
    def _compute_transfer_amount(self):
        for transaction in self:
            transaction.transfer_amount = transaction.securities * transaction.security_price

    @api.depends('transaction_type')
    def _compute_seller_id(self):
        for transaction in self.filtered(lambda t: t.transaction_type != 'sale'):
            transaction.seller_id = False

    def _compute_attachment_number(self):
        transaction_attachment_counts = dict(self.env['ir.attachment']._read_group(
            domain=[
                ('res_model', '=', 'equity.transaction'),
                ('res_id', 'in', self.ids),
            ],
            groupby=['res_id'],
            aggregates=['__count'],
        ))
        for transaction in self:
            transaction.attachment_number = transaction_attachment_counts.get(transaction.id, 0)

    @api.depends('transaction_type')
    def _compute_subscriber_id_placeholder(self):
        for transaction in self:
            if transaction.transaction_type == 'option':
                transaction.subscriber_id_placeholder = self.env._("Option Pool")
            else:
                transaction.subscriber_id_placeholder = self.env._("Unknown")

    @api.depends('partner_id.display_name', 'transaction_type')
    def _compute_display_name(self):
        type_values = dict(self._fields['transaction_type'].selection)
        for transaction in self:
            transaction.display_name = f'{transaction.partner_id.display_name} [{type_values.get(transaction.transaction_type)}]'

    @api.model_create_multi
    def create(self, vals_list):
        self.env['equity.cap.table'].invalidate_model()
        return super().create(vals_list)

    def write(self, vals):
        self.env['equity.cap.table'].invalidate_model()
        return super().write(vals)

    def action_transaction_seller_send(self):
        return self.action_transaction_send(for_seller=True)

    def action_transaction_subscriber_send(self):
        return self.action_transaction_send()

    def action_transaction_send(self, for_seller=False):
        self.ensure_one()
        holder = self.seller_id if for_seller else self.subscriber_id
        holder_type = self.env._("seller") if for_seller else self.env._("subscriber")
        if not holder:
            raise ValidationError(self.env._("No %s was set!", holder_type))
        return holder.action_partner_send(linked_transaction=self)

    def action_open_parent_transaction_form(self):
        self.ensure_one()
        if not self.parent_transaction_id:
            raise ValidationError(self.env._("No related options issuance transaction was found"))
        return self.parent_transaction_id._get_records_action()

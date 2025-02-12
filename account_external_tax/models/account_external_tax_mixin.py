# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models, Command
from odoo.modules.registry import Registry
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime


class AccountExternalTaxMixin(models.AbstractModel):
    """ Main class to add support for external tax integration on a model.

    This mixin can be inherited on models that should support external tax integration. Certain methods
    will need to be overridden, they are indicated below.
    """
    _name = 'account.external.tax.mixin'
    _description = 'Mixin to manage common parts of external tax calculation'

    is_tax_computed_externally = fields.Boolean(
        compute='_compute_is_tax_computed_externally',
        help='Technical field to determine if tax is calculated using an external service instead of Odoo.'
    )

    # Methods to be extended by tax calculation integrations (e.g. Avatax)
    # ====================================================================
    @api.depends('fiscal_position_id')
    def _compute_is_tax_computed_externally(self):
        """ When True external taxes will be calculated at the appropriate times. This should be overridden
        so the field is set for eligible records (e.g., sale and/or purchase documents). """
        self.is_tax_computed_externally = False

    def _get_external_taxes(self):
        """ Required hook that should return tax information calculated by an external service.

        :returns: Dictionary line_to_base_lines that maps records to their related taxes. The related taxes dict should
            be a dict prepared by _default_external_tax_base_line().
        """
        return {}

    def _uncommit_external_taxes(self):
        """ Optional hook that will be called when an invoice is put back to draft and should be uncommitted. """
        return

    def _void_external_taxes(self):
        """ Optional hook that will be called when an invoice is deleted and should be voided. """
        return

    # Methods to be extended to add support for external tax calculation on a model (e.g. account.move)
    # =================================================================================================
    def _get_and_set_external_taxes_on_eligible_records(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This method will be called automatically when taxes need to be calculated. This should filter out records
        who don't need external tax calculation (`is_tax_computed_externally` not set) and also potentially filter
        out records that are confirmed, posted or not of the right type.
        """
        return

    def _get_lines_eligible_for_external_taxes(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This method will be called to decide what document lines to pass to the external tax integration and on which
        tax will be calculated. This should filter out lines that are not "real", like section lines etc.
        """
        return []

    def _get_line_data_for_external_taxes(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This method returns model-agnostic line data to be used when doing an external tax request. It filters
        lines that should be sent to the external tax service already (via _get_lines_eligible_for_external_taxes).
        The returned dict always includes at least the following keys: id, model_name, product_id, description, qty,
        uom_id, price_subtotal, price_unit, discount, is_refund.
        """
        return []

    def _get_date_for_external_taxes(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This returns the date of the record on which tax calculation should be based.
        """
        return

    # Other methods
    # ================
    def _set_external_taxes(self, mapped_taxes):
        for line, base_line in mapped_taxes.items():
            extra_tax_data = self.env["account.tax"]._export_base_line_extra_tax_data(base_line)
            line.write({
                "extra_tax_data": extra_tax_data,
                "tax_ids": [Command.set([int(tax_id) for tax_id in extra_tax_data["manual_tax_amounts"]])],
            })

    def _default_external_tax_base_line(self, record):
        if hasattr(record, '_prepare_base_line_for_taxes_computation'):
            return record._prepare_base_line_for_taxes_computation()
        else:
            return self.env['account.tax']._prepare_base_line_for_taxes_computation(record)

    @api.model
    def _update_external_tax_amounts(self, record_details, tax, tax_amount):
        """ Helper method to increase `tax` by `tax_amount` in manual_tax_amounts of `base_line`.

        :param base_line (dict): The base line to update, generated by `_prepare_base_line_for_taxes_computation()`.
        :param tax (Model<account.tax>): The tax to increase.
        :param tax (float): The tax amount to add. """
        if not record_details['manual_tax_amounts']:
            record_details['manual_tax_amounts'] = {}

        manual_tax_amounts = record_details['manual_tax_amounts']
        manual_tax_amounts.setdefault(str(tax.id), defaultdict(float))
        manual_tax_amounts[str(tax.id)]['tax_amount_currency'] += tax_amount

    def button_external_tax_calculation(self):
        self._get_and_set_external_taxes_on_eligible_records()
        return True

    def _enable_external_tax_logging(self, icp_name):
        """ Start logging requests for 30 minutes. """
        self.env['ir.config_parameter'].sudo().set_param(
            icp_name,
            (fields.Datetime.now() + timedelta(minutes=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        )

    def _log_external_tax_request(self, module_name, icp_name, message):
        """ Log when the ICP's value is in the future. """
        log_end_date = self.env['ir.config_parameter'].sudo().get_param(
            icp_name, ''
        )
        try:
            log_end_date = datetime.strptime(log_end_date, DEFAULT_SERVER_DATETIME_FORMAT)
            need_log = fields.Datetime.now() < log_end_date
        except ValueError:
            need_log = False
        if need_log:
            # This creates a new cursor to make sure the log is committed even when an
            # exception is thrown later in this request.
            self.env.flush_all()
            dbname = self._cr.dbname
            with Registry(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['ir.logging'].create({
                    'name': module_name,
                    'type': 'server',
                    'level': 'INFO',
                    'dbname': dbname,
                    'message': message,
                    'func': '',
                    'path': '',
                    'line': '',
                })

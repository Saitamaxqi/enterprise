from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    @api.model
    def _evaluate_deadline(self, company, return_type, return_type_external_id, date_from, date_to):
        if return_type_external_id == 'l10n_si_intrastat.si_intrastat_goods_return_type':
            return date_to + relativedelta(days=15)
        return super()._evaluate_deadline(company, return_type, return_type_external_id, date_from, date_to)

from odoo import api, fields, models


class L10n_Be_ReportsPeriodicVatXmlExport(models.TransientModel):
    _inherit = "l10n_be_reports.vat.return.submission.wizard"

    need_intrastat_goods_report = fields.Boolean(compute='_compute_need_intrastat_goods_return', compute_sudo=True)

    @api.depends('return_id')
    def _compute_need_intrastat_goods_return(self):
        # TODO lost: remove in master
        for record in self:
            record.need_intrastat_goods_report = False

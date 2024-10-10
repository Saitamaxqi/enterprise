# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10n_Es_Reports_Modelo130AeatBoeMod130ExportWizard(models.TransientModel):
    _inherit = ['l10n_es_reports.aeat.boe.mod111and115and303.export.wizard']
    _description = "BOE Export Wizard for (mod130)"

    MODELO_NUMBER = 130

    taxpayer_id = fields.Char(string="Taxpayer ID")
    taxpayer_first_name = fields.Char(string="Taxpayer first name")
    taxpayer_last_name = fields.Char(string="Taxpayer last name")

from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def get_paperformat(self):
        """ Force a blank paperformat for our audit report model.
        We do not want the reporting engine to select the default paperformat because it messes
        with our design (margins, ...). """

        if self.model == 'audit.report':
            return False

        return super().get_paperformat()

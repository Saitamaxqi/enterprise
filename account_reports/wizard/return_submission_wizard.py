from odoo import api, models, fields


class AccountReturnSubmissionWizard(models.TransientModel):
    _name = "account.return.submission.wizard"
    _description = "Return submission wizard"

    instructions = fields.Html(string="Instructions")
    return_id = fields.Many2one(comodel_name='account.return', required=True)

    def action_proceed_with_submission(self):
        self.ensure_one()
        return self.return_id._proceed_with_submission(options_to_inject=self._get_submission_options_to_inject())

    def _get_submission_options_to_inject(self):
        """
        Can be overidden

        Used to inject additional options inside the report options during submission of the return
        """
        # Hook for extension
        return {}

    @api.model
    def _open_submission_wizard(self, account_return, instructions=None):
        record_action = self.create({
            'instructions': instructions,
            'return_id': account_return.id if account_return else None,
        })._get_records_action(target='new')

        record_action['name'] = account_return.type_id.name

        record_action.setdefault('context', {})
        record_action['context'] |= {
            'dialog_size': 'large',
        }
        return record_action

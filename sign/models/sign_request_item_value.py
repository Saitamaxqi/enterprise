# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class SignRequestItemValue(models.Model):
    _name = 'sign.request.item.value'
    _description = "Signature Item Value"
    _rec_name = 'sign_request_id'

    sign_request_item_id = fields.Many2one('sign.request.item', string="Signature Request item", required=True,
                                           index=True, ondelete='cascade')
    sign_item_id = fields.Many2one('sign.item', string="Signature Item", required=True, ondelete='cascade')
    sign_request_id = fields.Many2one(string="Signature Request", required=True, ondelete='cascade', related='sign_request_item_id.sign_request_id')

    value = fields.Text()
    frame_value = fields.Text()
    frame_has_hash = fields.Boolean()

    def write(self, vals):
        for request_item in self:
            if updated_value := vals.get("value"):
                if request_item.sign_item_id.constant and updated_value != request_item.value:
                    raise UserError(_("Cannot update the value of a read-only sign item"))

        return super().write(vals)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SignItem(models.Model):
    _name = 'sign.item'
    _description = "Fields to be sign on Document"
    _order = "page asc, posY asc, posX asc"
    _rec_name = 'template_id'

    template_id = fields.Many2one('sign.template', string="Document Template", required=True, ondelete='cascade')

    type_id = fields.Many2one('sign.item.type', string="Type", required=True, ondelete='restrict')

    required = fields.Boolean(default=True)
    responsible_id = fields.Many2one("sign.item.role", string="Responsible", ondelete="restrict")

    option_ids = fields.Many2many("sign.item.option", string="Selection options")

    radio_set_id = fields.Many2one("sign.item.radio.set", string="Radio button options", ondelete='cascade')
    num_options = fields.Integer(related="radio_set_id.num_options")

    name = fields.Char(string="Field Name", default=lambda self: self.type_id.placeholder)
    page = fields.Integer(string="Document Page", required=True, default=1)
    posX = fields.Float(digits=(4, 3), string="Position X", required=True)
    posY = fields.Float(digits=(4, 3), string="Position Y", required=True)
    width = fields.Float(digits=(4, 3), required=True)
    height = fields.Float(digits=(4, 3), required=True)
    alignment = fields.Char(default="center", required=True)

    transaction_id = fields.Integer(copy=False)

    def create(self, vals_list):
        res = super().create(vals_list)
        # All new sign items of type "radio" that don't have a radio_set_id
        # are grouped together in on radio set.
        hanging_radio_items = res.filtered(lambda item: item.type_id.item_type == "radio" and not item.radio_set_id)
        if hanging_radio_items:
            self.env['sign.item.radio.set'].create([{
                'radio_items': hanging_radio_items,
            }])
        return res

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        # When duplicating sign items of type "radio" create new equivalent radio sets for the new items.
        radio_set_map = {}
        for radio_set_id in {item['radio_set_id'] for item in vals_list if item['radio_set_id']}:
            new_radio_set = self.env['sign.item.radio.set'].create([{}])
            radio_set_map[radio_set_id] = new_radio_set.id
        for item in vals_list:
            item['radio_set_id'] = radio_set_map.get(item['radio_set_id'])
        return vals_list

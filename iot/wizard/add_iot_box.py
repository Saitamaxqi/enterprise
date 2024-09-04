# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import random
import requests
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError

TIMEOUT = 20


class AddIotBox(models.TransientModel):
    _name = 'add.iot.box'
    _description = 'Add IoT Box wizard'

    def _default_token(self):
        """Generates the url to provide an IoT Box to connect to the database.
        This url contains the url of the db, a generated token, the db_uuid and the enterprise_code.
        The generated token is valid for 15 minutes, enough time to pair an IoT Box with the database.
        The token is stored in the ir.config_parameter table to be used later by the "iot.box" once a
        new record is created.

        :return: the url to provide to the IoT Box to connect to the database
        """
        ir_config_parameter = self.env['ir.config_parameter'].sudo()
        generated_token = secrets.token_hex(16)
        saved_token = ir_config_parameter.search([('key', '=', 'iot_token')], limit=1)
        if saved_token:
            # token is valid for 15 minutes (enough to connect an IoT Box)
            if (
                saved_token.value
                and saved_token.write_date + timedelta(minutes=15) > fields.Datetime.now()
            ):
                generated_token = saved_token.value  # keep the old token
            else:
                saved_token.write({'value': generated_token})
        else:
            ir_config_parameter.create({'key': 'iot_token', 'value': generated_token})

        db_uuid = ir_config_parameter.get_param('database.uuid', default='')
        enterprise_code = ir_config_parameter.get_param('database.enterprise_code', default='')
        return f"{self.get_base_url()}?token={generated_token}&db_uuid={db_uuid}&enterprise_code={enterprise_code}"

    token = fields.Char(string='Token', default=_default_token, store=False)
    pairing_code = fields.Char(string='Pairing Code')
    use_token = fields.Boolean(string='Use other method', default=False)

    def box_pairing(self):
        if not self.pairing_code:
            raise UserError(_("Please enter a pairing code."))

        data = {
            'params': {
                'pairing_code': self.pairing_code,
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'database_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                'enterprise_code': self.env['ir.config_parameter'].sudo().get_param('database.enterprise_code'),
                'token': self.env['ir.config_parameter'].sudo().get_param('iot_token'),
            },
        }
        try:
            req = requests.post('https://iot-proxy.odoo.com/odoo-enterprise/iot/connect-db', json=data, timeout=TIMEOUT)
        except requests.exceptions.ReadTimeout:
            raise UserError(_("We had troubles pairing your IoT Box. Please try again later."))

        response = req.json()

        if 'error' in response:
            if response['error']['code'] == 404:
                raise UserError(_(
                    "The pairing code you provided was not found in our system. Please check that you "
                    "entered it correctly."
                ))
            else:
                raise requests.exceptions.ConnectionError()
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': _("Using Pairing Code to connect..."),
                    'sticky': False,
                    'params': {
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                },
            }

    def toggle_connection_method(self):
        """Toggle the connection method between token and pairing code

        :return: reloads the modal with the new connection method
        """
        self.use_token = not self.use_token
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'name': _('Connect my IoT Box'),
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    # TODO: Dead code to remove
    # Since https://github.com/odoo/enterprise/pull/68394 we don't need to reload the page anymore
    # For clients that did not upgrade, we keep this method as their old views still call it
    def reload_page(self):
        return self.env["ir.actions.actions"]._for_xml_id("iot.iot_box_action")

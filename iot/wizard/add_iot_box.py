# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models

import logging
import requests

_logger = logging.getLogger(__name__)


class AddIotBox(models.TransientModel):
    _name = 'add.iot.box'
    _description = 'Add IoT Box wizard'

    # Depending on the stage different window actions are available
    stage = fields.Selection([
        ('start', 'Start'),
        ('connect', 'Connect'),
        ('manual', 'Manual'),
    ], string='Stage', default='start')

    # IoT Box identifying fields and methods
    def _get_box_name(self, iot_box):
        serial = iot_box['serial_number'] or ""
        return _("IoT Box %(serial_n)s %(pairing_code)s", serial_n=serial, pairing_code=iot_box['pairing_code'])

    def _get_selection_value(self, iot_box):
        return f"{iot_box['pairing_code']} {iot_box['pairing_uuid']} {iot_box['serial_number'] or ''}"

    def _get_pairing_code_from_selection(self, selection):
        return selection.split()[0]

    def _get_serial_number_from_selection(self, selection):
        s_split = selection.split()
        return s_split[2] if len(s_split) == 3 else ""

    def _get_iot_box_to_connect_selection(self):
        discovered_iot_boxes = self._discover_boxes()
        selection = [(self._get_selection_value(iot_box), self._get_box_name(iot_box)) for iot_box in discovered_iot_boxes] if discovered_iot_boxes else []
        return selection

    iot_box_to_connect = fields.Selection(selection=_get_iot_box_to_connect_selection)
    serial_number = fields.Char(string='Serial Number', help="Serial number of the IoT Box")
    pairing_code = fields.Char(string='Pairing Code', help="Pairing code of the IoT Box")

    # ------------------------- IOT-PROXY CALLING METHODS -------------------------
    def _discover_boxes(self):
        """
        Calls the route /odoo-enterprise/iot/discover-boxes to get the IoT Boxes listed on the same network as the caller
        Returns a list of dictionaries containing the pairing code and serial number of the IoT Boxes

        :return: list with dictionaries each containing {'id': ..., 'serial_number': ..., 'pairing_code': ..., 'pairing_uuid': ...}
        """
        try:
            response = requests.get(
                'https://iot-proxy.odoo.com/odoo-enterprise/iot/discover-boxes',
                json={},
                timeout=5,
            )
            response.raise_for_status()

            result = response.json().get('result')  # e.g [{'id': 1, 'serial_number': 'sn1', 'pairing_code': 'pc1', 'pairing_uuid': 'pu1'}]
            if result:
                return result
            else:
                _logger.info("No IoT Boxes found registered on the local network")
        except (requests.exceptions.RequestException, ValueError):
            _logger.exception("Failed to contact iot-proxy to discover local IoT Boxes")
        return []

    def _connect_iot_box_with_pairing_code(self):
        """
        Calls the route /odoo-enterprise/iot/connect-db to connect the IoT Box with the provided pairing code

        :return: the action to open the wizard view with the next step
        """
        # Pairing code can be entered manually or recovered from the selected IoT Box
        if self.iot_box_to_connect:
            self.pairing_code = self._get_pairing_code_from_selection(self.iot_box_to_connect)
            self.serial_number = self._get_serial_number_from_selection(self.iot_box_to_connect)
        try:
            icp_sudo = self.env['ir.config_parameter'].sudo()
            response = requests.post(
                'https://iot-proxy.odoo.com/odoo-enterprise/iot/connect-db',
                json={
                    'params': {
                        'pairing_code': self.pairing_code,
                        'database_url': self.get_base_url(),
                        'token': self.env['iot.box']._default_token(),
                        'db_uuid': icp_sudo.get_param('database.uuid'),
                        'enterprise_code': icp_sudo.get_param('database.enterprise_code'),
                    },
                },
                timeout=5
            )

            response.raise_for_status()
            json = response.json()

            # Typically occurs when the used pairing code wasn't found on iot proxy
            error = json.get('error')  # e.g {'code': 404, 'message': '404: Not Found', ...}
            if error:
                _logger.warning("Error when using pairing code %s. IoT Proxy responded with an error message: %s", self.pairing_code, error)
                return self._open_no_iot_box_found_action()
            result = json.get('result')  # e.g [{'id': 1, 'serial_number': '12345'}]}
            if result and result[0]:
                return self._open_connecting_action()
            else:
                _logger.warning("Failed to connect the IoT Box with pairing code %s: %s", self.pairing_code, json)
        except (requests.exceptions.RequestException, ValueError):
            _logger.exception("Failed to use the provided pairing code %s to connect an iot box", self.pairing_code)
        return self._open_no_iot_box_found_action()

    # ------------------------- WIZARD OPEN ACTIONS -------------------------
    def _open_select_box_to_connect_action(self):
        self.stage = 'connect'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'add.iot.box',
            'res_id': self.id,
            'name': _("Several IoT's detected"),
            'view_mode': 'form',
            'view_id': self.env.ref('iot.view_select_box_to_connect').id,
            'target': 'new',
        }

    def _open_enter_pairing_code_action(self):
        self.stage = 'connect'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'add.iot.box',
            'res_id': self.id,
            'name': _("We couldn't detect any IoT"),
            'view_mode': 'form',
            'view_id': self.env.ref('iot.view_enter_pairing_code').id,
            'target': 'new',
        }

    def _open_no_iot_box_found_action(self):
        self.stage = 'manual'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'add.iot.box',
            'res_id': self.id,
            'name': _("We couldn't detect any IoT"),
            'view_mode': 'form',
            'view_id': self.env.ref('iot.view_no_iot_box_found').id,
            'target': 'new',
        }

    def _open_connecting_action(self):
        name = _('Connecting to IoT Box %s', self.serial_number) if self.serial_number else _('Connecting to IoT Box')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'add.iot.box',
            'res_id': self.id,
            'name': name,
            'view_mode': 'form',
            'view_id': self.env.ref('iot.view_add_iot_box').id,
            'target': 'new',
        }

    def open_documentation_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.odoo.com/documentation/master/applications/general/iot/iot_box.html',
            'target': 'new',
        }

    # ------------------------- WIZARD STAGE ACTIONS -------------------------

    def _start_stage(self):
        """
        Make a request to discover local IoT Boxes
        If none are found, open the pairing code wizard
        If only 1 is found, attempt to connect it directly
        If > 1 is found, open the select box wizard
        """
        detected_iot_boxes = self._get_iot_box_to_connect_selection()
        n_detected_iot_boxes = len(detected_iot_boxes) if detected_iot_boxes else 0

        # If multiple IoT Boxes are found, ask the user to select one
        if n_detected_iot_boxes > 1:
            return self._open_select_box_to_connect_action()
        # If only one IoT Box is found, connect it directly without showing the wizard to the user
        elif n_detected_iot_boxes == 1:
            self.pairing_code = self._get_pairing_code_from_selection(detected_iot_boxes[0][0])
            self.serial_number = self._get_serial_number_from_selection(detected_iot_boxes[0][0])
            return self._connect_iot_box_with_pairing_code()
        # If no IoT Boxes are found, ask the user to enter the pairing code manually
        else:
            return self._open_no_iot_box_found_action()

    def add_iot_box_wizard_action(self):
        """
        Base action for the wizard used to connect IoT Boxes
        Depending on the stage of the wizard, different actions are available
        """
        match self.stage:
            case 'start':
                return self._start_stage()
            case 'manual':
                return self._open_enter_pairing_code_action()
            case 'connect':
                return self._connect_iot_box_with_pairing_code()

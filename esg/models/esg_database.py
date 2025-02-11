import datetime
import json
import logging
import math
import re
import requests
from requests.exceptions import HTTPError, RequestException

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class EsgDatabase(models.Model):
    _name = 'esg.database'
    _description = 'Database'

    name = fields.Char(required=True)
    url = fields.Char()
    image = fields.Binary()
    last_update = fields.Date()
    latest_version = fields.Date()
    color = fields.Integer(compute='_compute_kanban_display')
    kanban_text = fields.Char(compute='_compute_kanban_display')

    @api.depends('latest_version', 'last_update')
    def _compute_kanban_display(self):
        for db in self:
            db.color = False
            db.kanban_text = self.env._("Not loaded")
            if not db.last_update:
                continue
            formatted_date = format_date(self.env, db.last_update, date_format='MMMM y')
            db.kanban_text = self.env._("Updated on: %(date)s", date=formatted_date)
            if db.last_update >= db.latest_version:
                db.color = 7
            else:
                db.color = 2

    @api.ondelete(at_uninstall=False)
    def _prevent_database_deletion(self):
        ademe_db = self.env.ref('esg.esg_database_ademe')
        if any(db == ademe_db for db in self):
            raise ValidationError(self.env._("You can't delete the ADEME database."))

    def action_load_data(self):
        self.ensure_one()
        if self == self.env.ref('esg.esg_database_ademe', raise_if_not_found=False):
            result = self._action_import_ademe_file()
        else:
            raise ValidationError(self.env._("Database file is missing"))
        if result['params']['type'] == "success":
            self.last_update = self.latest_version
        return result

    def _external_api_call(self, request_url):
        ademe_api_url = 'https://data.ademe.fr/data-fair/api/v1/datasets/base-carboner'
        if not request_url.startswith(ademe_api_url):
            raise ValidationError(self.env._('Invalid URL.'))
        response_error = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                },
            }
        try:
            request_response = requests.request(
                'GET',
                request_url,
                timeout=(30, 30),
            )
            request_response.raise_for_status()
        except (ValueError, HTTPError, RequestException) as exception:
            response_error['params']['message'] = self.env._(
                "Server returned an unexpected error: %(error)s",
                error=(request_response.text or str(exception)),
            )
            return response_error

        try:
            response_text = request_response.text
            response_data = json.loads(response_text)
        except json.JSONDecodeError:
            response_error['params']['message'] = self.env._("JSON response could not be decoded.")
            return response_error

        return response_data

    # =============
    # ADEME IMPORT
    # =============
    def _get_ademe_emission_factor_values(self, lines):
        existing_factors = dict(self.env['esg.emission.factor']._read_group(
            domain=[('database_id', '=', self.id)],
            groupby=['code'],
            aggregates=['id:recordset'],
        ))
        gasses = {
            'CO2f': self.env.ref('esg.esg_gas_co2'),
            'CH4f': self.env.ref('esg.esg_gas_ch4f'),
            'CH4b': self.env.ref('esg.esg_gas_ch4b'),
            'N2O': self.env.ref('esg.esg_gas_n2o'),
            'SF6': self.env.ref('esg.esg_gas_sf6'),
        }
        hardcoded_units_conversion = {
            'kg': [
                'kg of active substance', 'kg (live weight)', 'kg net weight', 'kg of spreaded nitrogen',
                'kg of suppressed DCO', 'kg of treated leather', 'Kg', 'kg of spreaded nitrgen',
                'kgH2', 'kg NTK', 'kg BioGNC'
            ],
            'L': ['liter', 'Liter'],
            'Ton': ['ton', 'ton of K2O', 'ton of N', 'ton of P2O5', 'ton of clinker', 'ton of waste', 'tonne'],
            'Units': ['unit', 'meal'],
            'm': ['m of road'],
            'm²': ['m²  net floor area', 'm² of ceiling', 'm² of floor', 'm² of wall', 'm2 SHON'],
            'm³': ['m3', 'm3 (n)'],
            'ml': ['mL'],
            'Hours': ['hour', 'heure'],
            'kWh': ['kWh (LHV)', 'kWh (PCI)', 'kWh HHV', 'kWh ICV', 'kWh IVC', 'kWh LHV', 'kWh SCV']
        }
        hardcoded_source_scopes = {
            'Achats de biens': 'indirect_others',
            'Process et émissions fugitives': 'direct',
            'Achats de services': 'indirect_others',
            'Combustibles': 'direct',
            'Transport de marchandises': 'indirect_others',
            'Transport de personnes': 'indirect_others',
            'Statistiques territoriales': 'direct',
            'UTCF': 'direct',
            'Traitement des déchets': 'indirect_others',
            'Electricité': 'indirect',
            'Réseaux de chaleur / froid': 'direct',
        }

        def _get_gas_lines(line, gasses, total_emissions):
            gas_lines = []
            for gas in ['CO2f', 'CH4f', 'CH4b', 'N2O']:
                if line.get(gas, 0) > 0:
                    gas_lines.append({
                        'gas_id': gasses[gas],
                        'quantity': line[gas],
                        'activity_type_id': line.get('Type_poste', False),
                    })
            for i in range(1, 6):
                additional_gas = line.get(f"Code_gaz_supplémentaire_{i}", None)
                if additional_gas and additional_gas in ['SF6']:
                    gas_lines.append({
                        'gas_id': gasses[additional_gas],
                        'quantity': line.get(f"Valeur_gaz_supplémentaire_{i}", 0),
                        'activity_type_id': line.get('Type_poste', False),
                    })
            # if the gaz decomposition is equal to the total emissions, that means that the decomposition
            # is given with CO2 equivalent value; each line needs to be adapted to have the gaz volume instead
            if not float_compare(sum(gas['quantity'] for gas in gas_lines), total_emissions, precision_rounding=0.1):
                for gas in gas_lines:
                    gas['quantity'] = gas['quantity'] / gas['gas_id'].global_warming_potential

            return gas_lines

        _logger.info("ESG: Processing raw lines")
        line_values = []
        posts_gas_lines = []
        for raw_line in lines:
            if not raw_line:
                continue
            line = raw_line  # dict(zip(dict_keys, raw_line))
            if line["Statut_de_l'élément"] == "Archivé" or\
                line["Type_de_l'élément"] == "Données source":
                continue

            total_emissions = line['Total_poste_non_décomposé']
            if line["Type_Ligne"] == "Poste":
                posts_gas_lines += _get_gas_lines(line, gasses, total_emissions)
                line_values[-1]['gas_line_ids'] = posts_gas_lines
                continue

            dates = {}
            for raw_date in ['Date_de_création', 'Période_de_validité']:
                if raw_date not in line:
                    dates[raw_date] = False
                    continue
                try:
                    dates[raw_date] = datetime.datetime.strptime(line[raw_date], '%Y-%m-%d')
                except ValueError:
                    dates[raw_date] = False

            posts_gas_lines = []
            gas_lines = _get_gas_lines(line, gasses, total_emissions)

            normalized_unit = line.get('Unité_anglais', line.get('Unité_français', '')).replace('kgCO2e/', '')
            for base_unit, alternate_names in hardcoded_units_conversion.items():
                if normalized_unit in alternate_names:
                    normalized_unit = base_unit
                    break

            factor_values = {
                'name': f'{line.get("Nom_base_anglais", "")} {line.get("Nom_attribut_anglais", "")} {line.get("Nom_frontière_anglais", "")}'
                    if line.get("Nom_base_anglais", '')
                    else f'{line.get("Nom_base_français", "")} {line.get("Nom_attribut_français", "")} {line.get("Nom_frontière_français", "")}',
                'code': line["Identifiant_de_l'élément"],
                'database_id': self.id,
                'uom_id': normalized_unit,
                'esg_uncertainty_value': line.get('Incertitude', 0) / 100,
                'compute_method': 'physically',
                'valid_from': dates['Date_de_création'],
                'valid_to': dates['Période_de_validité'],
                'source_id': line['Code_de_la_catégorie'],
                'gas_line_ids': gas_lines,
            }
            if not gas_lines:
                factor_values['esg_emissions_value'] = total_emissions
            line_values.append(factor_values)

        _logger.info("ESG: Checking existing units, emission sources and esg activity type")
        # Prepare to process all units at once to avoid multiplying queries and loops
        units = [line['uom_id'].strip() for line in line_values]
        existing_units = dict(
            self.env['uom.uom']._read_group(
                domain=[('name', 'in', units)],
                groupby=['name'],
                aggregates=['id:recordset'],
            )
        )
        # Prepare to process all sources at once to avoid multiplying queries and loops
        source_tree_list = []
        for line in line_values:
            source_tree_list.append([s.strip() for s in line['source_id'].split('>')])
        all_sources_name = {item for sublist in source_tree_list for item in sublist}
        existing_sources = {(name, parent): record for name, parent, record in self.env['esg.emission.source']._read_group(
            domain=[('name', 'in', all_sources_name)],
            groupby=['name', 'parent_id'],
            aggregates=['id:recordset'],
        )}

        # Prepare to process all activity types at once to avoid multiplying queries and loops
        existing_activity_types = dict(
            self.env['esg.activity.type']._read_group(
                domain=[],
                groupby=['name'],
                aggregates=['id:recordset'],
            )
        )

        _logger.info("ESG: Processing link to related records")
        # slow loop, should be optimized
        for source_tree, unit, line in zip(source_tree_list, units, line_values):
            # units
            existing_unit = existing_units.get(unit, False)
            if not existing_unit:
                existing_unit = self.env['uom.uom'].create({'name': unit})
                existing_units[unit] = existing_unit
            line['uom_id'] = existing_unit.id
            # sources
            previous_existing_source = self.env['esg.emission.source']
            for source_name in source_tree:
                existing_source = existing_sources.get((source_name, previous_existing_source), False)
                if not existing_source:
                    existing_source = self.env['esg.emission.source'].create({
                        'name': source_name,
                        'parent_id': previous_existing_source.id,
                        'scope': hardcoded_source_scopes.get(source_name, previous_existing_source.scope) or 'direct',
                    })
                    existing_sources[source_name, previous_existing_source] = existing_source
                previous_existing_source = existing_source
            line['source_id'] = previous_existing_source.id
            # activity types + declare gas lines correctly
            if line['gas_line_ids']:
                for gas_line in line['gas_line_ids']:
                    gas_line['gas_id'] = gas_line['gas_id'].id
                    if not gas_line['activity_type_id']:
                        continue
                    activity = existing_activity_types.get(gas_line['activity_type_id'], False)
                    if not activity:
                        activity = self.env['esg.activity.type'].create({'name': gas_line['activity_type_id']})
                        existing_activity_types[gas_line['activity_type_id']] = activity
                    gas_line['activity_type_id'] = activity.id
                line['gas_line_ids'] = [Command.create(gas) for gas in line['gas_line_ids']]

        new_factor_values = []
        write_factor_values = {}
        for line_value in line_values:
            # Separate data into existing one and new one
            line_code = line_value['code']
            if line_code in existing_factors:
                write_factor_values[existing_factors[line_code]] = line_value
            else:
                new_factor_values.append(line_value)
        return new_factor_values, write_factor_values

    def _action_import_ademe_file(self):
        ademe_api_url = 'https://data.ademe.fr/data-fair/api/v1/datasets/base-carboner'
        ademe_data = self._external_api_call(ademe_api_url)
        if not ademe_data.get('updatedAt'):
            return ademe_data
        ademe_data['updatedAt'] = re.sub(r'\.\d+', '', ademe_data['updatedAt'])
        self.latest_version = datetime.datetime.strptime(ademe_data['updatedAt'], "%Y-%m-%dT%H:%M:%SZ")
        if self.last_update and self.latest_version <= self.last_update:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': self.env._('ADEME data is already up to date.'),
                },
            }

        required_calls = math.ceil(ademe_data['count'] / 10000)  # the api limits the amount of data lines to 10k

        complete_data = []
        for i in range(0, required_calls):
            data_url = f'{ademe_api_url}/lines?size=10000&format=json&after={10000 * i}'
            data = self._external_api_call(data_url)
            if not data.get('results', None):
                return data
            complete_data += data['results']

        _logger.info("ESG: Importing ADEME carbon base file")
        try:
            new_values, write_values = self._get_ademe_emission_factor_values(complete_data)
            _logger.info("ESG: Creating/Writing records")
            self.env['esg.emission.factor'].create(new_values)
            for record, values in write_values.items():
                record.gas_line_ids = False
                record.write(values)
            _logger.info("ESG: File imported")
        except KeyError as e:
            _logger.error(e)
            raise ValidationError(self.env._("The file format doesn't seem to be correct."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._('ADEME data has been successfully imported.'),
            },
        }

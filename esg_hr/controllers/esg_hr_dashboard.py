from odoo.http import request

from odoo.addons.esg.controllers.esg_dashboard import EsgDashboard


class EsgHrDashboard(EsgDashboard):

    def _get_gender_distribution_data(self):
        gender_selection = dict(request.env['esg.employee.report']._get_gender_selection())
        is_sample = False

        employee_count_per_gender = {
            gender_selection.get(gender): count
            for gender, count in request.env['hr.employee']._read_group(
                domain=[
                    ('company_id', 'in', request.env.companies.ids),
                    ('gender', '!=', False),
                ],
                groupby=['gender'],
                aggregates=['id:count'],
            )
        }
        if not employee_count_per_gender:
            employee_count_per_gender = dict.fromkeys(gender_selection.values(), 3)
            is_sample = True

        return {
            'data': employee_count_per_gender,
            'is_sample': is_sample,
        }

    def _build_graph_config(self, data, is_sample=False):
        # Pie chart showing gender distribution
        config = {
            'type': 'pie',
            'data': {
                'labels': list(data.keys()),
                'datasets': [
                    {
                        'label': self.env._('Count'),
                        'data': list(data.values()),
                    },
                ],
            },
            'options': {
                'aspectRatio': 4,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': False,
                    },
                },
            },
        }
        if is_sample:
            config['data']['datasets'][0]['backgroundColor'] = 'rgba(235, 235, 235, 1)'
        return config

    def _get_dashboard_data(self):
        data = super()._get_dashboard_data()
        if not self.env.user.has_group('hr.group_hr_user'):
            return data
        gender_distribution_data = self._get_gender_distribution_data()
        graph_config = self._build_graph_config(gender_distribution_data['data'], gender_distribution_data['is_sample'])
        return {
            **data,
            'gender_parity_box': {
                'graph_config': graph_config,
            },
        }

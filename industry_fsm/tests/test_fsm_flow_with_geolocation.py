# Part of Odoo. See LICENSE file for full copyright and licensing details

import time

from freezegun import freeze_time
from markupsafe import Markup

from odoo.http import _request_stack
from odoo.tests import tagged
from odoo.tools import DotDict

from .common import TestIndustryFsmCommon


@tagged('post_install', '-at_install')
class TestFsmFlowWithGeolocation(TestIndustryFsmCommon):
    def setUp(self):
        super().setUp()
        fake_req = DotDict({
            # various things go and access request items
            'httprequest': DotDict({
                'user_agent': {
                    'browser': 'chrome',
                },
                'environ': {'REMOTE_ADDR': 'localhost'},
                'cookies': {},
                'args': {},
            }),
            'cookies': {},
            # bypass check_identity flow
            'session': {'identity-check-last': time.time()},
            'geoip': {
                'ip': "test.geoip",
            # /!\ Attention: don't touch city and country_code, they should be not be null !!
            # it will result on calling a real external api each time to render them
            # from lon and lat !!
                'city': {
                    'name': 'Namur',
                },
                'country_code': "be",
            },
        })
        _request_stack.push(fake_req)

    def tearDown(self):
        super().tearDown()
        _request_stack.pop()

    def test_start_timer_with_geolocation(self):
        self.fsm_project.allow_geolocation = True
        task_with_george_user = self.task.with_user(self.george_user)
        geolocation_context = {
            "geolocation": {
                "success": True,
                "latitude": 10,
                "longitude": 13,
            }
        }

        expected_time = '2017-01-01 00:00:00'
        with freeze_time(expected_time):
            task_with_george_user.with_context(geolocation_context).action_timer_start()

        self.assertEqual(self.task.message_ids.sorted('create_date')[0].body, Markup('<p>Timer started at: 01/01/2017 00:00:00<br>GPS Coordinates: Namur, Belgium (10, 13)<a href="https://maps.google.com?q=10,13" target="_blank">View on Map</a></p>'))

        expected_time = '2017-01-01 12:20:00'
        with freeze_time(expected_time):
            action = task_with_george_user.action_timer_stop()
            geolocation_context["geolocation"]["latitude"] = 200.56
            geolocation_context["geolocation"]["longitude"] = 300.25
            wizard = self.env['hr.timesheet.stop.timer.confirmation.wizard'] \
                .with_context({**action['context'], **geolocation_context}) \
                .with_user(self.george_user) \
                .new({})
            wizard.action_save_timesheet()

        self.assertEqual(self.task.message_ids.sorted('create_date')[0].body, Markup('<p>Timer stopped at: 01/01/2017 12:20:00<br>GPS Coordinates: Namur, Belgium (200.56, 300.25)<a href="https://maps.google.com?q=200.56,300.25" target="_blank">View on Map</a></p>'))

    def test_start_timer_with_geolocation_with_denied_geolocation_permissions(self):
        self.fsm_project.allow_geolocation = True
        task_with_george_user = self.task.with_user(self.george_user)
        geolocation_context = {
            "geolocation": {
                "success": False,
                "message": "Location error: {Error returned by the browser, related to denied permission or maybe something else} e.g User denied Geolocation",
            }
        }

        expected_time = '2017-01-01 00:00:00'
        with freeze_time(expected_time):
            task_with_george_user.with_context(geolocation_context).action_timer_start()

        self.assertEqual(self.task.message_ids.sorted('create_date')[0].body, Markup('<p>Timer started at: 01/01/2017 00:00:00<br>Location error: {Error returned by the browser, related to denied permission or maybe something else} e.g User denied Geolocation</p>'))

        expected_time = '2017-01-01 12:20:00'
        with freeze_time(expected_time):
            action = task_with_george_user.action_timer_stop()
            geolocation_context["geolocation"]["latitude"] = 200.56
            geolocation_context["geolocation"]["longitude"] = 300.25
            wizard = self.env['hr.timesheet.stop.timer.confirmation.wizard'] \
                .with_context({**action['context'], **geolocation_context}) \
                .with_user(self.george_user) \
                .new({})
            wizard.action_save_timesheet()

        self.assertEqual(self.task.message_ids.sorted('create_date')[0].body, Markup('<p>Timer stopped at: 01/01/2017 12:20:00<br>Location error: {Error returned by the browser, related to denied permission or maybe something else} e.g User denied Geolocation</p>'))

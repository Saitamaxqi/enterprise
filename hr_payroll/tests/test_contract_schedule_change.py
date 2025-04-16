# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Date
from odoo.tests import tagged, TransactionCase
from dateutil.relativedelta import relativedelta

@tagged('post_install', '-at_install', 'contract_schedule_change')
class TestContractScheduleChange(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Richard',
        })
        cls.calendars = cls.env['resource.calendar'].create([
            {'name': 'Calendar 1', 'full_time_required_hours': 40},
            {'name': 'Calendar 2', 'full_time_required_hours': 50},
            {'name': 'Calendar 3', 'full_time_required_hours': 60},
            {'name': 'Calendar 4', 'full_time_required_hours': 70},
        ])

    def test_base_case(self):
        self.employee.version_id.write({
            'date_version': Date.to_date('2020-01-01'),
            'contract_date_start': Date.to_date('2020-01-01'),
            'contract_date_end': Date.to_date('2020-01-31'),
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })
        contract_1 = self.employee.version_id

        contract_2 = self.employee.create_version({
            'date_version': Date.to_date('2020-02-01'),
            'contract_date_start': Date.to_date('2020-02-01'),
            'contract_date_end': Date.to_date('2020-02-28'),
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })

        #Normally they shouldn't be tagged for calendar_changed
        self.assertFalse(contract_1.calendar_changed)
        self.assertFalse(contract_2.calendar_changed)

        #Now if any of those two contracts has a different schedule they should be tagged
        #We have to access contract_2 first to trigger the compute, normally it will be computed correctly since it is stored
        contract_2.resource_calendar_id = self.calendars[1]
        self.assertTrue(contract_2.calendar_changed)
        self.assertTrue(contract_1.calendar_changed)

        #Reset
        contract_2.resource_calendar_id = self.calendars[0]
        self.assertFalse(contract_2.calendar_changed)
        self.assertFalse(contract_1.calendar_changed)

        #Other way around
        contract_1.resource_calendar_id = self.calendars[1]
        self.assertTrue(contract_1.calendar_changed)
        self.assertTrue(contract_2.calendar_changed)

    def test_future_contract(self):
        # This test is the same as the base case except the second contract is set in the futur
        self.employee.version_id.write({
            'date_version': Date.today() + relativedelta(months=-1),
            'contract_date_start': Date.today() + relativedelta(months=-1),
            'contract_date_end': Date.today() + relativedelta(months=1),
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })
        contract_1 = self.employee.version_id
        contract_2 = self.employee.create_version({
            'date_version': Date.today() + relativedelta(months=1, days=1),
            'contract_date_start': Date.today() + relativedelta(months=1, days=1),
            'contract_date_end': False,
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })

        #Normally they shouldn't be tagged for calendar_changed
        self.assertFalse(contract_1.calendar_changed)
        self.assertFalse(contract_2.calendar_changed)

        #Now if any of those two contracts has a different schedule they should be tagged
        #We have to access contract_2 first to trigger the compute, normally it will be computed correctly since it is stored
        contract_2.resource_calendar_id = self.calendars[1]
        self.assertTrue(contract_2.calendar_changed)
        self.assertTrue(contract_1.calendar_changed)

        #Reset
        contract_2.resource_calendar_id = self.calendars[0]
        self.assertFalse(contract_2.calendar_changed)
        self.assertFalse(contract_1.calendar_changed)

        #Other way around
        contract_1.resource_calendar_id = self.calendars[1]
        self.assertTrue(contract_1.calendar_changed)
        self.assertTrue(contract_2.calendar_changed)

    def test_triple_contract(self):
        #Simulates a temporary part time
        #For this test we will have 3 contracts, the one in the middle will have the different schedule
        self.employee.version_id.write({
            'date_version': Date.to_date('2020-01-01'),
            'contract_date_start': Date.to_date('2020-01-01'),
            'contract_date_end': Date.to_date('2020-01-31'),
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })
        contract_1 = self.employee.version_id

        contract_2 = self.employee.create_version({
            'date_version': Date.to_date('2020-02-01'),
            'contract_date_start': Date.to_date('2020-02-01'),
            'contract_date_end': Date.to_date('2020-02-28'),
            'resource_calendar_id': self.calendars[1].id,
            'wage': 1337,
        })
        contract_3 = self.employee.create_version({
            'date_version': Date.to_date('2020-03-01'),
            'contract_date_start': Date.to_date('2020-03-01'),
            'contract_date_end': Date.to_date('2020-03-31'),
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })

        #They should all be tagged for calendar_changed and 2, 3 should point to their predecessor
        self.assertTrue(contract_3.calendar_changed)
        self.assertTrue(contract_2.calendar_changed)
        self.assertTrue(contract_1.calendar_changed)

        #Change the middle contract to have the same schedule as the 2 other ones
        contract_2.resource_calendar_id = self.calendars[0]
        self.assertFalse(contract_2.calendar_changed)
        #Everything should be reset
        self.assertFalse(contract_1.calendar_changed)
        self.assertFalse(contract_3.calendar_changed)

        #Revert
        contract_2.resource_calendar_id = self.calendars[1]
        self.assertTrue(contract_2.calendar_changed)
        #Make sure it's back to the orifinal state
        self.assertTrue(contract_1.calendar_changed)
        self.assertTrue(contract_3.calendar_changed)
        #The same should also happen if the contract is cancelled
        contract_2.unlink()
        #There is a change in calendar due to the gap between the contracts
        self.assertTrue(contract_1.calendar_changed)
        self.assertTrue(contract_3.calendar_changed)

    def test_four_contracts(self):
        #All four contracts will have different schedules
        self.employee.version_id.write({
            'date_version': Date.to_date('2020-01-01'),
            'contract_date_start': Date.to_date('2020-01-01'),
            'contract_date_end': Date.to_date('2020-01-31'),
            'resource_calendar_id': self.calendars[0].id,
            'wage': 1337,
        })
        contract_1 = self.employee.version_id
        contract_2 = self.employee.create_version({
            'date_version': Date.to_date('2020-02-01'),
            'contract_date_start': Date.to_date('2020-02-01'),
            'contract_date_end': Date.to_date('2020-02-28'),
            'resource_calendar_id': self.calendars[1].id,
            'wage': 1337,
        })
        contract_3 = self.employee.create_version({
            'date_version': Date.to_date('2020-03-01'),
            'contract_date_start': Date.to_date('2020-03-01'),
            'contract_date_end': Date.to_date('2020-03-31'),
            'resource_calendar_id': self.calendars[2].id,
            'wage': 1337,
        })
        contract_4 = self.employee.create_version({
            'date_version': Date.to_date('2020-04-01'),
            'contract_date_start': Date.to_date('2020-04-01'),
            'contract_date_end': Date.to_date('2020-04-30'),
            'resource_calendar_id': self.calendars[3].id,
            'wage': 1337,
        })

        #Make sure everything is correct from the start, access in reverse order for initial compute
        self.assertTrue(contract_4.calendar_changed)
        self.assertTrue(contract_3.calendar_changed)
        self.assertTrue(contract_2.calendar_changed)
        self.assertTrue(contract_1.calendar_changed)

        #Two pairs, only two of them should stay tagged after this
        contract_2.resource_calendar_id = self.calendars[0]
        self.assertTrue(contract_2.calendar_changed)
        contract_3.resource_calendar_id = self.calendars[3]
        self.assertTrue(contract_3.calendar_changed)
        self.assertFalse(contract_1.calendar_changed)
        self.assertFalse(contract_4.calendar_changed)

        #Cancel the second and have the same schedule on the first as third and fourth
        contract_2.unlink()
        contract_1.resource_calendar_id = self.calendars[3]
        self.assertTrue(contract_1.calendar_changed) # True due to gap being big enough
        self.assertTrue(contract_3.calendar_changed) # True due to gap
        self.assertFalse(contract_4.calendar_changed) # Simply false

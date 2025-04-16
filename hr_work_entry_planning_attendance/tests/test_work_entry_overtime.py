# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_work_entry_attendance.tests.common import HrWorkEntryAttendanceCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install', 'work_entry_overtime')
class TestPayslipOvertime(HrWorkEntryAttendanceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract.write({
            'work_entry_source': "planning",
            'overtime_from_attendance': True,
        })
        cls.attendance_type = cls.env.ref('hr_work_entry.work_entry_type_attendance')
        cls.overtime_type = cls.env.ref('hr_work_entry.work_entry_type_overtime')
        cls.work_entry_type_public_type_off = cls.env['hr.work.entry.type'].create({
            'name': 'Public Time Off',
            'code': 'PUBLIC',
            'is_leave': True,
        })

        # Generates a slot for the monrning/afternoon every day of december 2022
        planning_slot_vals = []
        for i in range(1, 31):
            for hour_start in [7, 12]:
                start_dt = datetime(2022, 12, i, hour_start, 0, 0)
                if start_dt.weekday() >= 5:
                    continue
                planning_slot_vals.append({
                    'resource_id': cls.contract.employee_id.resource_id.id,
                    'start_datetime': start_dt,
                    'end_datetime': start_dt + relativedelta(hours=4),
                    'state': 'published',
                })
        cls.slots = cls.env['planning.slot'].create(planning_slot_vals)

    def _check_work_entry(self, entry, expected_date_start, expected_date_stop, expected_type):
        self.assertEqual(entry.date_start, expected_date_start)
        self.assertEqual(entry.date_stop, expected_date_stop)
        self.assertEqual(entry.work_entry_type_id, expected_type)

    def _check_work_entries(self, entries, expected_values_list):
        self.assertEqual(len(entries), len(expected_values_list))
        for entry, expected_values in zip(entries, expected_values_list):
            self._check_work_entry(entry, *expected_values)

    def test_01_no_overtime(self):
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self._check_work_entries(work_entries, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

    def _test_02_overtime_classic_day_before_after(self, overtime_from_attendance, expected_work_entries_values):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_02_overtime_classic_day_before_after(self):
        self._test_02_overtime_classic_day_before_after(True, [
            (datetime(2022, 12, 12, 6, 0), datetime(2022, 12, 12, 7, 0), self.overtime_type),
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 11, 0), datetime(2022, 12, 12, 12, 0), self.overtime_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
            (datetime(2022, 12, 12, 16, 0), datetime(2022, 12, 12, 20, 0), self.overtime_type),
        ])

    def test_02bis_overtime_classic_day_before_after(self):
        self._test_02_overtime_classic_day_before_after(False, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

    def _test_03_overtime_classic_day_before(self, overtime_from_attendance, expected_work_entries_values):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 15),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_03_overtime_classic_day_before(self):
        self._test_03_overtime_classic_day_before(True, [
            (datetime(2022, 12, 12, 6, 0), datetime(2022, 12, 12, 7, 0), self.overtime_type),
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 11, 0), datetime(2022, 12, 12, 12, 0), self.overtime_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

    def test_03bis_overtime_classic_day_before(self):
        self._test_03_overtime_classic_day_before(False, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

    def _test_04_overtime_classic_day_after(self, overtime_from_attendance, expected_work_entries_values):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 11),
            'check_out': datetime(2022, 12, 12, 17),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_04_overtime_classic_day_after(self):
        self._test_04_overtime_classic_day_after(True, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 11, 0), datetime(2022, 12, 12, 12, 0), self.overtime_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
            (datetime(2022, 12, 12, 16, 0), datetime(2022, 12, 12, 17, 0), self.overtime_type),
        ])

    def test_04bis_overtime_classic_day_after(self):
        self._test_04_overtime_classic_day_after(False, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

    def test_05_overtime_week_end(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 10, 11),
            'check_out': datetime(2022, 12, 10, 17),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 10), date(2022, 12, 10)).sorted('date_start')
        self._check_work_entries(work_entries, [
            (datetime(2022, 12, 10, 11, 0), datetime(2022, 12, 10, 17, 0), self.overtime_type),
        ])

    def test_06_no_overtime_public_time_off_whole_day(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self._check_work_entries(work_entries, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 11, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def _test_07_overtime_public_time_off_whole_day(self, overtime_from_attendance, expected_work_entries_values):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 20),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_07_overtime_public_time_off_whole_day(self):
        self._test_07_overtime_public_time_off_whole_day(True, [
            (datetime(2022, 12, 26, 6, 0), datetime(2022, 12, 26, 20, 0), self.overtime_type),
        ])

    def test_07bis_overtime_public_time_off_whole_day(self):
        self._test_07_overtime_public_time_off_whole_day(False, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 11, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def _test_08_overtime_public_time_off_half_day(self, overtime_from_attendance, expected_work_entries_values):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 11),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_08_overtime_public_time_off_half_day(self):
        self._test_08_overtime_public_time_off_half_day(True, [
            (datetime(2022, 12, 26, 6, 0), datetime(2022, 12, 26, 11, 0), self.overtime_type),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def test_08bis_overtime_public_time_off_half_day(self):
        self._test_08_overtime_public_time_off_half_day(False, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 11, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def _test_09_overtime_public_time_off_1_hour(self, overtime_from_attendance, expected_work_entries_values):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 10),
            'check_out': datetime(2022, 12, 26, 11),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_09_overtime_public_time_off_1_hour(self):
        self._test_09_overtime_public_time_off_1_hour(True, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 10, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 10, 0), datetime(2022, 12, 26, 11, 0), self.overtime_type),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def test_09bis_overtime_public_time_off_1_hour(self):
        self._test_09_overtime_public_time_off_1_hour(False, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 11, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def _test_10_overtime_public_time_off_1_hour_inside(self, overtime_from_attendance, expected_work_entries_values):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 9),
            'check_out': datetime(2022, 12, 26, 10),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_10_overtime_public_time_off_1_hour_inside(self):
        self._test_10_overtime_public_time_off_1_hour_inside(True, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 9, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 9, 0), datetime(2022, 12, 26, 10, 0), self.overtime_type),
            (datetime(2022, 12, 26, 10, 0), datetime(2022, 12, 26, 11, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def test_10bis_overtime_public_time_off_1_hour_inside(self):
        self._test_10_overtime_public_time_off_1_hour_inside(False, [
            (datetime(2022, 12, 26, 7, 0), datetime(2022, 12, 26, 11, 0), self.work_entry_type_public_type_off),
            (datetime(2022, 12, 26, 12, 0), datetime(2022, 12, 26, 16, 0), self.work_entry_type_public_type_off),
        ])

    def test_11_overtime_classic_day_under_threshold(self):
        self.contract.company_id.overtime_company_threshold = 15
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 15),
            'check_out': datetime(2022, 12, 12, 16, 13),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self._check_work_entries(work_entries, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

    def _test_12_overtime_classic_day_below_threshold(self, overtime_from_attendance, expected_work_entries_values):
        self.contract.company_id.overtime_company_threshold = 15
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 15),
            'check_out': datetime(2022, 12, 12, 16, 18),
        })
        self.contract.overtime_from_attendance = overtime_from_attendance
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self._check_work_entries(work_entries, expected_work_entries_values)

    def test_12_overtime_classic_day_below_threshold(self):
        self._test_12_overtime_classic_day_below_threshold(True, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
            (datetime(2022, 12, 12, 16, 0), datetime(2022, 12, 12, 16, 18), self.overtime_type),
        ])

    def test_12bis_overtime_classic_day_below_threshold(self):
        self._test_12_overtime_classic_day_below_threshold(False, [
            (datetime(2022, 12, 12, 7, 0), datetime(2022, 12, 12, 11, 0), self.attendance_type),
            (datetime(2022, 12, 12, 12, 0), datetime(2022, 12, 12, 16, 0), self.attendance_type),
        ])

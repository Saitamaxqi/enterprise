import { calendarView } from "@web/views/calendar/calendar_view";
import { PayRunCalendarController } from "./hr_payslip_run_calendar_controller";
import { registry } from "@web/core/registry";
import { PayRunCalendarModel } from "./hr_payslip_run_calendar_model";


const PayRunCalendarView = {
    ...calendarView,
    Controller: PayRunCalendarController,
    Model: PayRunCalendarModel,
    buttonTemplate: "hr_payroll.PayRunCalendarView.Buttons"
};

registry.category("views").add("pay_run_calendar", PayRunCalendarView);

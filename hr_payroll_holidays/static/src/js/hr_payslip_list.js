import { TimeOffToDeferWarning, useTimeOffToDefer } from "@hr_payroll_holidays/views/hooks";
import { payslipListView } from "@hr_payroll/views/payslip_list/hr_payslip_list_controller";
import { registry } from "@web/core/registry";
import { PayslipListRenderer } from "@hr_payroll/views/payslip_list/hr_payslip_list_renderer";

class PayslipHolidaysListRenderer extends PayslipListRenderer {
    static template = "hr_payroll_holidays.PayslipListRenderer";
    static components = { ...PayslipListRenderer.components, TimeOffToDeferWarning };

    setup() {
        super.setup();
        this.timeOff = useTimeOffToDefer();
    }
}

payslipListView.Renderer = PayslipHolidaysListRenderer;

const payslipRunListView = {
    ...payslipListView,
    Renderer: PayslipHolidaysListRenderer,
};

registry.category("views").add("hr_payroll_payslip_run_list", payslipRunListView);

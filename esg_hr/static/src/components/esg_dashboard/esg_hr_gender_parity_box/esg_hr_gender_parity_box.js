import { EsgGraphDashboard } from "@esg/components/esg_dashboard/esg_graph_dashboard/esg_graph_dashboard";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class EsgHrGenderParityBox extends Component {
    static template = "esg_hr.GenderParityBox";
    static components = { EsgGraphDashboard };
    static props = {
        data: Object,
    };

    setup() {
        this.actionService = useService("action");
    }

    openEmployeeReportLeadershipViews() {
        this.actionService.doAction("esg_hr.action_esg_employee_report_gender_parity");
    }
}

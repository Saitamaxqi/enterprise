import { EsgDashboard } from "@esg/components/esg_dashboard/esg_dashboard";
import { EsgHrGenderParityBox } from "@esg_hr/components/esg_dashboard/esg_hr_gender_parity_box/esg_hr_gender_parity_box";
import { patch } from "@web/core/utils/patch";

patch(EsgDashboard, {
    components: {
        ...EsgDashboard.components,
        EsgHrGenderParityBox,
    },
});

patch(EsgDashboard.prototype, {
    get dashboardComponents() {
        return {
            ...super.dashboardComponents,
            4: {
                component: EsgHrGenderParityBox,
                props: {
                    data: this.data.gender_parity_box,
                },
            },
        };
    },
});

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { Component, useState, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon;


export class AccountReturnDashboardList extends Component {
    static template = "account_reports.account_return_dashboard_list";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.accountReturns = useState([]);
        onWillStart(this.fetchNextReturns);
    }

    formatReturn(accountReturn) {
        const deadlineDate = parseDate(accountReturn.date_deadline);
        const now = DateTime.now().startOf('day');
        const daysDiff = deadlineDate.diff(now, 'days').days;

        let deadlineDisplay;
        let deadlineClass = '';

        if (daysDiff < -1) {
            deadlineDisplay = _t("Due on %s", formatDate(deadlineDate));
            deadlineClass = 'text-danger';
        } else if (daysDiff === -1) {
            deadlineDisplay = _t("Due Yesterday");
            deadlineClass = 'text-danger';
        } else if (daysDiff === 0) {
            deadlineDisplay = _t("Due Today");
            deadlineClass = 'text-warning';
        } else if (daysDiff === 1) {
            deadlineDisplay = _t("Due Tomorrow");
            deadlineClass = 'text-warning';
        } else if (daysDiff <= 5) {
            deadlineDisplay = _t("Due in %s days", Math.round(daysDiff));
            deadlineClass = 'text-warning';
        } else {
            deadlineDisplay = _t("Due in %s days", Math.round(daysDiff));
        }

        return {
            id: accountReturn.id,
            name: accountReturn.name,
            deadline: formatDate(deadlineDate),
            deadlineDisplay,
            deadlineClass,
        };
    }

    async fetchNextReturns() {
        const returns = await this.orm.call(
            'account.return',
            'get_next_return_for_dashboard',
            [this.props.record.resId], //allow_multiple_by_types
        );

        this.accountReturns = returns.map(this.formatReturn);
    }
}


export const accountReturnDashboardList = {
    component: AccountReturnDashboardList,
}

registry.category("view_widgets").add("account_return_dashboard_list", accountReturnDashboardList);

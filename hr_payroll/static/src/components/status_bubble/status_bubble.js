import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class StatusBubble extends Component {
    static template = "hr_payroll.StatusBubble";
    static props = {
        record: { type: Object },
        warningCount: { type: Number, optional: true },
        errorCount: { type: Number, optional: true },
        removeStates: { type: Array, optional: true },
    };
    static defaultProps = {
        warningCount: 0,
        errorCount: 0,
        removeStates: [],
    };

    setup() {
        this.selection = this.props.record.fields.state.selection.filter(
            (o) => !this.props?.removeStates.includes(o[0])
        );
    }

    get activeIndex() {
        return this.selection.findIndex(([key]) => key === this.props.record.data.state);
    }
}

export class StatusBubbleField extends StatusBubble {
    static props = { ...standardFieldProps, ...StatusBubble.props };
}

export const statusBubbleField = {
    component: StatusBubbleField,
    displayName: _t("Status Bubble"),
    supportedOptions: [
        {
            label: _t("Warning Count"),
            name: "warning_count",
            type: "integer",
        },
        {
            label: _t("Error Count"),
            name: "error_count",
            type: "integer",
        },
        {
            label: _t("Remove State"),
            name: "remove_states",
            type: "string",
        },
    ],
    supportedTypes: ["many2one", "selection"],
    extractProps({ options }) {
        return {
            warningCount: options.warning_count,
            errorCount: options.error_count,
            removeStates: options.remove_states,
        };
    },
};

registry.category("fields").add("hr_payroll_status_bubble", statusBubbleField);

import { BadgeField } from "@web/views/fields/badge/badge_field";
import { registry } from "@web/core/registry";

import { useService } from "@web/core/utils/hooks";

export class CallStatusBadgeField extends BadgeField {
    static template = "voip.CallStatusBadgeField";

    setup() {
        super.setup();
        this.userAgent = useService("voip.user_agent");
    }

    get iconClass() {
        const direction = this.props.record.data.direction;
        if (direction === "outgoing") {
            return "oi oi-arrow-up-right";
        }
        if (direction === "incoming") {
            return "oi oi-arrow-down-left";
        }
        return "";
    }

    get statusLabel() {
        const state = this.props.record.data.state;
        const mapping = {
            missed: "Missed Call",
            aborted: "Cancelled Call",
            terminated:
                this.props.record.data.direction === "incoming" ? "Incoming call" : "Outgoing call",
            rejected: "Rejected Call",
            ongoing:
                this.userAgent.session?.call?.id === this.props.record.data.id
                    ? "Ongoing Call"
                    : "Ended unexpectedly",
            calling:
                this.userAgent.session?.call?.id === this.props.record.data.id
                    ? "Trying to call"
                    : "Ended unexpectedly",
        };
        return mapping[state] || "Unknown";
    }

    get badgeClass() {
        const state = this.props.record.data.state;
        if (state === "rejected" || state === "missed") {
            return "text-bg-danger";
        }
        if (state === "aborted") {
            return "text-bg-secondary";
        }
        if (state === "calling" || state === "ongoing") {
            return "text-bg-warning";
        }
        return "text-bg-success";
    }
}

registry.category("fields").add("call_status_badge", {
    component: CallStatusBadgeField,
    displayName: "Call Status Badge",
    supportedTypes: ["char", "selection"],
});

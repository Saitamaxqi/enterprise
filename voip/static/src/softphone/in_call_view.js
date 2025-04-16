import { Component, useEffect } from "@odoo/owl";

import { Call } from "@voip/core/call_model";
import { ActionButton } from "@voip/softphone/action_button";
import { UserInfo } from "@voip/softphone/user_info";

import { useService } from "@web/core/utils/hooks";

export class InCallView extends Component {
    static components = { ActionButton, UserInfo };
    static props = { call: Call };
    static template = "voip.InCallView";

    setup() {
        this.action = useService("action");
        this.userAgent = useService("voip.user_agent");
        this.ui = useService("ui");
        useEffect(
            // Pair the state of the UI with the state of the tracks, so if it
            // says you're muted, you can be confident you're muted.
            () => this.userAgent.updateTracks(),
            () => [this.isMuted, this.isOnHold]
        );
    }

    /** @returns {boolean} */
    get isOnHold() {
        return this.userAgent.session?.isOnHold ?? false;
    }

    /** @returns {boolean} */
    get isMuted() {
        return this.userAgent.session?.isMute ?? false;
    }

    onClickContact(ev) {
        const action = {
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "form"]],
            target: this.ui.isSmall ? "new" : "current",
            context: {},
        };
        if (this.props.call.partner) {
            action.res_id = this.props.call.partner.id;
        } else {
            action.context.default_phone = this.props.call.phoneNumber;
        }
        this.action.doAction(action);
    }

    onClickHangUp() {
        this.userAgent.hangup();
    }

    onClickHold() {
        this.userAgent.setHold(!this.isOnHold);
    }

    onClickMute() {
        this.userAgent.session.isMute = !this.userAgent.session.isMute;
    }
}

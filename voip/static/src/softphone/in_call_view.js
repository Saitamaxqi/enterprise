import { Component, useEffect } from "@odoo/owl";

import { Call } from "@voip/core/call_model";
import { ActionButton } from "@voip/softphone/action_button";
import { ContactInfo } from "@voip/softphone/contact_info";
import { Keypad } from "@voip/softphone/keypad";

import { useService } from "@web/core/utils/hooks";

export class InCallView extends Component {
    static components = { ActionButton, ContactInfo, Keypad };
    static props = { call: Call };
    static template = "voip.InCallView";

    setup() {
        this.action = useService("action");
        this.softphone = useService("voip").softphone;
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
    get isKeypadOpen() {
        return this.softphone.inCallView.keypad.isOpen;
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
        if (this.props.call.partner_id) {
            action.res_id = this.props.call.partner_id.id;
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

    onClickKeypad() {
        this.softphone.inCallView.keypad.isOpen = !this.isKeypadOpen;
    }

    onClickMute() {
        this.userAgent.session.isMute = !this.userAgent.session.isMute;
    }
}

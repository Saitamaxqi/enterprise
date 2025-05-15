import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class VoipSystrayItem extends Component {
    static props = {};
    static template = "voip.SystrayItem";

    setup() {
        this.voip = useService("voip");
        this.ringtoneService = useService("voip.ringtone");
        this.userAgent = useService("voip.user_agent");
        this.softphone = this.voip.softphone;
    }

    /** @returns {string} */
    get iconClass() {
        if (this.userAgent.session?.isOnHold) {
            return "fa fa-pause";
        }
        return "oi oi-voip";
    }

    /**
     * Number of missed calls used to display in systray item icon.
     *
     * @returns {number}
     */
    get missedCallCount() {
        return this.voip.missedCalls;
    }

    /** @returns {boolean} */
    get shouldDisplayInCallIndicator() {
        const call = this.userAgent.session?.call;
        if (!call) {
            return false;
        }
        return call.isInProgress && call.state === "ongoing";
    }

    /**
     * Translated text used as the title attribute of the systray item.
     *
     * @returns {string}
     */
    get titleText() {
        return this.softphone.isDisplayed ? _t("Close Softphone") : _t("Open Softphone");
    }

    /** @returns {string} */
    get systrayButtonClasses() {
        if (this.userAgent.hasCallInvitation) {
            return "text-success";
        }
        if (!this.shouldDisplayInCallIndicator) {
            return "";
        }
        if (this.userAgent.session?.isOnHold) {
            return "rounded-pill px-2 bg-warning-subtle text-warning-emphasis";
        }
        return "rounded-pill px-2 bg-success-subtle text-success-emphasis";
    }

    /** @param {MouseEvent} ev */
    onClick(ev) {
        if (this.softphone.isDisplayed) {
            this.softphone.hide();
            if (this.userAgent.hasCallInvitation) {
                this.ringtoneService.stopPlaying();
            }
        } else {
            this.softphone.show();
            this.voip.resetMissedCalls();
            if (this.userAgent.shouldPlayIncomingCallRingtone) {
                this.ringtoneService.incoming.play();
            }
        }
    }
}

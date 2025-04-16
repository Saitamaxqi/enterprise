import { Component } from "@odoo/owl";

import { Call } from "@voip/core/call_model";
import { ActionButton } from "@voip/softphone/action_button";
import { UserInfo } from "@voip/softphone/user_info";

import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";

/**
 * "Abstract" component defining useful properties that are shared between
 * CallInvitation and InCallView.
 */
export class CallView extends Component {
    static components = { ActionButton, UserInfo };
    static props = { call: Call };
    static template = "";

    /** @returns {string} */
    get avatarAlt() {
        if (!this.contact) {
            return _t("Default profile picture");
        }
        return _t("Profile picture of %(user)", { user: this.contact.name });
    }

    /** @returns {string} */
    get avatarUrl() {
        if (!this.contact) {
            return "/base/static/img/avatar_grey.png";
        }
        return url("/web/image", {
            model: "res.partner",
            id: this.contact.id,
            field: "avatar_128",
        });
    }

    /** @returns {import("@mail/core/common/persona_model").Persona} */
    get contact() {
        return this.props.call.partner;
    }

    /** @returns {string} */
    get contactInfo() {
        if (!this.contact) {
            return ""; // TODO
        }
        const info = [];
        if (this.contact.commercial_company_name) {
            info.push(this.contact.commercial_company_name);
        }
        // ⚠ French: function = job position
        if (this.contact.function) {
            info.push(this.contact.function);
        }
        return info.join(", ");
    }

    /** @returns {string} */
    get contactName() {
        return this.contact?.voipName || this.props.call.phoneNumber;
    }
}

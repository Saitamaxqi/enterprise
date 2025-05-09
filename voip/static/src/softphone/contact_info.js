import { Component } from "@odoo/owl";

import { Call } from "@voip/core/call_model";

import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";

/**
 * Displays general information (avatar, name, etc.) about the contact
 * associated with the given call.
 */
export class ContactInfo extends Component {
    static defaultProps = { extraClass: "" };
    static props = { call: Call, extraClass: { type: String, optional: true } };
    static template = "voip.ContactInfo";

    /** @returns {string} */
    get avatarAlt() {
        if (!this.contact) {
            return _t("Default profile picture");
        }
        return _t("Profile picture of %(user)s", { user: this.contact.name });
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
        return this.props.call.partner_id;
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
        return this.contact?.voipName || this.props.call.phone_number;
    }
}

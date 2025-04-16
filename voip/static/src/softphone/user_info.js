import { Component } from "@odoo/owl";

/**
 * Generic component that defines the general structure of user info.
 */
export class UserInfo extends Component {
    static defaultProps = { extraClass: "", avatarClass: "" };
    static props = {
        extraClass: { type: String, optional: true },
        avatarClass: { type: String, optional: true },
        hideAvatar: { type: Boolean, optional: true },
        name: { type: String, optional: true },
        avatarUrl: { type: String, optional: true },
        avatarAlt: { type: String, optional: true },
        subtitle: { type: String, optional: true },
    };
    static template = "voip.UserInfo";
}

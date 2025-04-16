import { Component } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export const FOREVER = luxon.DateTime.utc(9999, 12, 31);

/**
 * Do Not Disturb (DND) selector.
 */
export class DndSelector extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "voip.DndSelector";
    static props = {};

    setup() {
        this.settings = useService("mail.store").settings;
    }

    get badgeTitle() {
        if (!this.doNotDisturbUntilDt || this.doNotDisturbUntilDt <= luxon.DateTime.now()) {
            return _t("Available");
        }
        if (this.doNotDisturbUntilDt.toMillis() === FOREVER.toMillis()) {
            return _t("Do Not Disturb until I turn it back on");
        }
        return _t("Do Not Disturb until %(time)s", {
            time: this.doNotDisturbUntilDt.toLocaleString(luxon.DateTime.DATETIME_MED),
        });
    }

    get doNotDisturbUntilDt() {
        return this.settings.do_not_disturb_until_dt;
    }

    get dndButtonBottomText() {
        if (!this.doNotDisturbUntilDt || this.doNotDisturbUntilDt <= luxon.DateTime.now()) {
            return _t("Incoming calls will be muted");
        }
        if (this.doNotDisturbUntilDt.toMillis() === FOREVER.toMillis()) {
            return _t("Until I turn it back on");
        }
        return _t("Until %(time)s", {
            time: this.doNotDisturbUntilDt.toLocaleString(luxon.DateTime.DATETIME_MED),
        });
    }
}

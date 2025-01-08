import { Record } from "@mail/core/common/record";
import { Settings } from "@mail/core/common/settings_model";

import { FOREVER } from "@voip/softphone/do_not_disturb_selector";

import { serializeDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

patch(Settings.prototype, {
    setup() {
        super.setup();
        /** @type {luxon.DateTime} */
        this.do_not_disturb_until_dt = Record.attr(undefined, {
            type: "datetime",
            onUpdate() {
                clearTimeout(this.resetDoNotDisturbTimeoutId);
                if (
                    !this.do_not_disturb_until_dt ||
                    this.do_not_disturb_until_dt <= luxon.DateTime.now() ||
                    this.do_not_disturb_until_dt.toMillis() == FOREVER.toMillis()
                ) {
                    return;
                }
                this.resetDoNotDisturbTimeoutId = setTimeout(() => {
                    this.do_not_disturb_until_dt = null;
                }, this.do_not_disturb_until_dt.diffNow().as("milliseconds"));
            },
        });
        /** @type {number} */
        this.resetDoNotDisturbTimeoutId;
    },

    setVoipDoNotDisturb(minutes) {
        if (minutes === 0) {
            // available
            this.do_not_disturb_until_dt = null;
        } else if (minutes === -1) {
            this.do_not_disturb_until_dt = FOREVER;
        } else {
            this.do_not_disturb_until_dt = luxon.DateTime.now().plus({ minutes });
        }
        this._saveVoipSettings();
    },

    async _saveVoipSettings() {
        await this.store.env.services.orm.call(
            "res.users.settings",
            "set_res_users_settings",
            [[this.id]],
            {
                new_settings: {
                    do_not_disturb_until_dt: this.do_not_disturb_until_dt
                        ? serializeDateTime(this.do_not_disturb_until_dt)
                        : false,
                },
            }
        );
    },
});

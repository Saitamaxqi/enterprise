import { fields, Record } from "@mail/core/common/record";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

export class Call extends Record {
    static id = "id";
    static _name = "voip.call";
    /** @type {Object.<number, Call>} */
    static records = {};

    /**
     * @param {Object} data
     * @returns {Call}
     */
    update(data) {
        super.update(...arguments);
        if (data.partner_id) {
            this.partner_id = this.store.Persona.insert({ ...data.partner_id, type: "partner" });
        }
        if (data.create_date) {
            this.create_date = deserializeDateTime(data.create_date);
        }
        if (data.startDate) {
            this.startDate = deserializeDateTime(data.startDate);
        }
        if (data.end_date) {
            this.end_date = deserializeDateTime(data.end_date);
        }
    }

    activity;
    /** @type {string} */
    country_code_from_phone;
    /** @type {luxon.DateTime} */
    create_date;
    /** @type {"incoming"|"outgoing"} */
    direction;
    /** @type {string} */
    display_name;
    /** @type {luxon.DateTime} */
    end_date;
    /** @type {import("@mail/core/persona_model").Persona | undefined} */
    partner_id;
    /** @type {string} */
    phone_number;
    /** @type {luxon.DateTime} */
    startDate;
    /** @type {"aborted"|"calling"|"missed"|"ongoing"|"rejected"|"terminated"} */
    state = fields.Attr("calling", {
        onUpdate() {
            const currentCall = this.store.env.services["voip.user_agent"].session?.call;
            if (!currentCall) {
                return;
            }
            if (!this.eq(currentCall)) {
                return;
            }
            switch (this.state) {
                case "aborted":
                case "missed":
                case "rejected":
                case "terminated": {
                    const softphone = this.store.env.services.voip.softphone;
                    softphone.showSummary(this);
                    break;
                }
                default:
                    return;
            }
        },
    });
    /** @type {{ interval: number, time: number }} */
    timer;

    /** @returns {string} */
    get callDate() {
        if (this.state === "terminated") {
            return this.startDate.toLocaleString(luxon.DateTime.TIME_SIMPLE);
        }
        return this.create_date.toLocaleString(luxon.DateTime.TIME_SIMPLE);
    }

    /** @returns {number} */
    get duration() {
        if (!this.startDate || !this.end_date) {
            return 0;
        }
        return (this.end_date - this.startDate) / 1000;
    }

    /** @returns {string} */
    get durationString() {
        return this._formatTimerText(this.duration);
    }

    /** @returns {boolean} */
    get isInProgress() {
        switch (this.state) {
            case "calling":
            case "ongoing":
                // In case the power goes out in the middle of a call (for
                // example), the call may be stuck in the “calling” or “ongoing”
                // state, meaning we can't rely on the state alone, hence the
                // need to also check for the session.
                return Boolean(this.store.env.services["voip.user_agent"].session);
            default:
                return false;
        }
    }

    /** @returns {string} */
    get timerText() {
        return this._formatTimerText(this.timer?.time);
    }

    /**
     * @param {number|undefined} seconds
     * @returns {string}
     */
    _formatTimerText(seconds) {
        if (!seconds) {
            return _t("%(minutes)s:%(seconds)s", { minutes: "00", seconds: "00" });
        }
        if (seconds < 3600) {
            return _t("%(minutes)s:%(seconds)s", {
                minutes: String(Math.floor(seconds / 60)).padStart(2, "0"),
                seconds: String(seconds % 60).padStart(2, "0"),
            });
        }
        return _t("%(hours)s:%(minutes)s:%(seconds)s", {
            hours: String(Math.floor(seconds / 3600)).padStart(2, "0"),
            minutes: String(Math.floor((seconds % 3600) / 60)).padStart(2, "0"),
            seconds: String(seconds % 60).padStart(2, "0"),
        });
    }
}

Call.register();

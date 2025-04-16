import { Component, useEffect, useRef } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { user } from "@web/core/user";

export class TabEntry extends Component {
    static defaultProps = { extraClass: "", subtitleClass: "" };
    static props = {
        avatarUrl: { type: String },
        countryCode: { type: String, optional: true },
        extraClass: { type: String, optional: true },
        title: { type: String },
        subtitle: { type: String, optional: true },
        subtitleClass: { type: String, optional: true },
        subtitleIcon: { type: String, optional: true },
        phoneNumber: { type: String },
        record: Object,
        slots: Object,
    };
    static template = "voip.TabEntry";

    setup() {
        this.regionNames = new Intl.DisplayNames(user.lang, { type: "region" });
        this.softphone = useService("voip").softphone;
        this.activeRecordRef = useRef("active-record");
        useEffect(
            (scrollToActiveRecord) => {
                if (!scrollToActiveRecord || !this.activeRecordRef.el) {
                    return;
                }
                scrollTo(this.activeRecordRef.el);
                this.softphone.callSummary.scrollToActiveRecord = false;
            },
            () => [this.softphone.callSummary.scrollToActiveRecord]
        );
        useEffect(
            (isActiveRecord) => {
                if (!isActiveRecord || !this.activeRecordRef.el) {
                    return;
                }
                scrollTo(this.activeRecordRef.el);
            },
            () => [this.isActiveRecord]
        );
    }

    /** @returns {string} */
    get flagAlt() {
        const country = this.regionNames.of(this.props.countryCode);
        return _t("%(country)s flag", { country });
    }

    /** @returns {boolean} */
    get isActiveRecord() {
        return this.props.record.eq(this.softphone.activeRecord);
    }

    /** @param {MouseEvent} ev */
    onClickSummary(ev) {
        this.softphone.activeRecord = this.isActiveRecord ? null : this.props.record;
    }
}

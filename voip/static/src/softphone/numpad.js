import { useSelection } from "@mail/utils/common/hooks";
import { Component, useEffect, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { useDebounced } from "@web/core/utils/timing";

export class Numpad extends Component {
    static props = { extraClass: { type: String, optional: true } };
    static defaultProps = { extraClass: "" };
    static template = "voip.Numpad";

    setup() {
        this.softphone = useService("voip").softphone;
        this.callService = useService("voip.call");
        this.userAgentService = useService("voip.user_agent");
        this.input = useRef("input");
        this.updateCountryCodeDebounced = useDebounced(() => this.updateCountryCode(), 300);
        this.selection = useSelection({
            refName: "input",
            model: this.softphone.numpad.selection,
        });
        this.regionNames = new Intl.DisplayNames(user.lang, { type: "region" });
        useEffect(
            (shouldFocus) => {
                if (shouldFocus) {
                    this.input.el.focus();
                    this.selection.restore();
                    this.softphone.shouldFocus = false;
                }
            },
            () => [this.softphone.shouldFocus]
        );
    }

    get flagAltLabel() {
        const country = this.regionNames.of(this.softphone.numpad.countryCode.toUpperCase());
        return _t("%(country)s flag", { country });
    }

    /** @param {MouseEvent} ev */
    onClickBackspace(ev) {
        const value = this.softphone.numpad.value.trim();
        const { selectionStart, selectionEnd } = this.input.el;
        const cursorPosition = selectionStart === selectionEnd && selectionStart !== 0 ? selectionStart - 1 : selectionStart;
        if (selectionStart !== 0) {
            this.softphone.numpad.value = value.slice(0, cursorPosition) + value.slice(selectionEnd);
            this.updateCountryCode();
        }
        this.selection.moveCursor(cursorPosition);
        this.softphone.shouldFocus = true;
    }

    onClickKey(key) {
        this.userAgentService.session?.sipSession?.sessionDescriptionHandler.sendDtmf(key);
        const value = this.softphone.numpad.value.trim();
        const { selectionStart, selectionEnd } = this.input.el;
        this.softphone.numpad.value = value.slice(0, selectionStart) + key + value.slice(selectionEnd);
        this.updateCountryCode();
        this.selection.moveCursor(selectionStart + 1);
        this.softphone.shouldFocus = true;
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        const inputValue = this.softphone.numpad.value.trim();
        if (!inputValue) {
            return;
        }
        this.userAgentService.makeCall({ phone_number: inputValue });
    }

    async updateCountryCode() {
        const phoneNumber = this.softphone.numpad.value.trim();
        if (!phoneNumber.startsWith("+") && !phoneNumber.startsWith("00")) {
            return;
        }
        const { country_code } = await rpc("/voip/get_country_code", {
            phone_number: this.softphone.numpad.value.trim(),
        });
        this.softphone.numpad.countryCode = country_code;
    }
}

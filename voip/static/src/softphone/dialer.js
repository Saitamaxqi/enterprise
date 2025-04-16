import { useSelection } from "@mail/utils/common/hooks";
import { htmlJoin } from "@mail/utils/common/html";

import { Component, htmlEscape, markup, useEffect, useRef } from "@odoo/owl";

import { ActionButton } from "@voip/softphone/action_button";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { escapeRegExp, unaccent } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";

const T9_MAPPING = Object.freeze({
    2: "ABC",
    3: "DEF",
    4: "GHI",
    5: "JKL",
    6: "MNO",
    7: "PQRS",
    8: "TUV",
    9: "WXYZ",
});

export class Dialer extends Component {
    static components = { ActionButton };
    static props = {};
    static template = "voip.Dialer";

    setup() {
        this.store = useService("mail.store");
        this.softphone = useService("voip").softphone;
        this.input = useRef("input");
        this.userAgentService = useService("voip.user_agent");
        this.voip = useService("voip");
        this.selection = useSelection({
            refName: "input",
            model: this.softphone.numpad.selection,
        });
        this.regionNames = new Intl.DisplayNames(user.lang, { type: "region" });
        useEffect(
            (shouldFocus) => {
                if (shouldFocus && !this.voip.error) {
                    this.input.el.focus();
                    this.selection.restore();
                    this.softphone.shouldFocus = false;
                }
            },
            () => [this.softphone.shouldFocus]
        );
        this.onInputChangeDebounced = useDebounced((ev) => {
            this.onInputSearchBar(ev);
            this.updateCountryCode();
        }, 300);
    }

    get calleeSuggestions() {
        const searchTerms = this.softphone.numpad.value.trim();
        if (!searchTerms) {
            return { length: 0 };
        }
        const uniqueMatches = new Set();
        const nameMatched = [];
        const phoneNumberMatched = [];
        const containsLetters = /[A-Z]/i.test(searchTerms);
        const looksLikeT9 = [...searchTerms].every((letter) => letter in T9_MAPPING);
        for (const contact of this.voip.softphone.contacts) {
            if (containsLetters) {
                const match = highlightMatch(contact.name, searchTerms);
                if (!match) {
                    continue;
                }
                uniqueMatches.add(contact.id);
                nameMatched.push({
                    contact,
                    id: contact.id + " (by name)",
                    match,
                });
                // Since it contains letters, it's neither a T9 code nor a phone
                // number: no need to go further.
                continue;
            }
            if (looksLikeT9) {
                const t9NameParts = contact.t9_name.trim().split(" ");
                for (let i = 0; i < t9NameParts.length; ++i) {
                    if (!t9NameParts[i].startsWith(searchTerms)) {
                        continue;
                    }
                    const nameParts = contact.name.split(" ");
                    const match = highlightT9Match(nameParts[i], searchTerms);
                    if (!match) {
                        console.warn(
                            `Unexpected mismatch between name and t9_name: "${contact.name}" and "${contact.t9_name}"`
                        );
                        break;
                    }
                    uniqueMatches.add(contact.id);
                    nameMatched.push({
                        contact,
                        id: contact.id + " (by name)",
                        match: markup(
                            [...nameParts.slice(0, i), match, ...nameParts.slice(i + 1)]
                                .map(htmlEscape)
                                .join(" ")
                        ),
                    });
                }
            }
            // TODO: refine phone number match
            const regex = new RegExp(`(^.*?)(${escapeRegExp(searchTerms)})(.*?$)`, "i");
            const [, before, match, after] = contact.phone.match(regex) ?? [];
            if (!match) {
                continue;
            }
            uniqueMatches.add(contact.id);
            phoneNumberMatched.push({
                contact,
                id: contact.id + " (by phone)",
                match: markup`${before}<span class="fw-bolder">${match}</span>${after}`,
            });
        }
        const length = uniqueMatches.size;
        let firstResult = null;
        if (length > 0) {
            firstResult = nameMatched[0] ?? phoneNumberMatched[0];
        }
        const searchResultsBySearchField = new Map();
        if (nameMatched.length > 0) {
            searchResultsBySearchField.set(_t("Name"), nameMatched);
        }
        if (phoneNumberMatched.length > 0) {
            searchResultsBySearchField.set(_t("Phone number"), phoneNumberMatched);
        }
        return { length, firstResult, searchResultsBySearchField };
    }

    /** @returns {string} ⚠ markup */
    get firstSuggestion() {
        const suggestion = this.calleeSuggestions.firstResult;
        const isMatchByName = suggestion.id.endsWith("(by name)");
        if (isMatchByName) {
            return markup`${suggestion.match} (${suggestion.contact.phone})`;
        }
        return markup`${suggestion.contact.voipName} (${suggestion.match})`;
    }

    get flagAltLabel() {
        if (!this.softphone.numpad.countryCode.iso) {
            return "";
        }
        const country = this.regionNames.of(this.softphone.numpad.countryCode.iso.toUpperCase());
        return _t("%(country)s flag", { country });
    }

    get keys() {
        return [
            { key: "1", letters: "" },
            { key: "2", letters: "ABC" },
            { key: "3", letters: "DEF" },
            { key: "4", letters: "GHI" },
            { key: "5", letters: "JKL" },
            { key: "6", letters: "MNO" },
            { key: "7", letters: "PQRS" },
            { key: "8", letters: "TUV" },
            { key: "9", letters: "WXYZ" },
            { key: "*", letters: "", icon: "fa-asterisk" },
            { key: "0", letters: "+" },
            { key: "#", letters: "", icon: "fa-hashtag" },
        ];
    }

    /**
     * Determines whether the cached country code (if any) still matches the
     * contents of the keypad input. Useful for hiding the flag and redoing the
     * request if the content of the input changes.
     *
     * @returns {boolean}
     */
    get phoneNumberStartsWithCountryCode() {
        if (!this.softphone.numpad.countryCode.itu) {
            return false;
        }
        let phoneNumber = this.softphone.numpad.value.trim();
        if (phoneNumber.startsWith("00")) {
            phoneNumber = phoneNumber.slice(2);
        } else if (phoneNumber.startsWith("+")) {
            phoneNumber = phoneNumber.slice(1);
        } else {
            return false;
        }
        return phoneNumber.startsWith(this.softphone.numpad.countryCode.itu);
    }

    get showOthersButtonText() {
        switch (this.calleeSuggestions.length) {
            case 0:
                return "";
            case 1:
                return _t("1 other…");
            case 2:
                return _t("2 others…");
            default:
                return _t("%s others…", this.calleeSuggestions.length);
        }
    }

    /** @param {MouseEvent} ev */
    onClickBackspace(ev) {
        const value = this.softphone.numpad.value.trim();
        const { selectionStart, selectionEnd } = this.input.el;
        const cursorPosition =
            selectionStart === selectionEnd && selectionStart !== 0
                ? selectionStart - 1
                : selectionStart;
        if (selectionStart !== 0) {
            this.softphone.numpad.value =
                value.slice(0, cursorPosition) + value.slice(selectionEnd);
            this.updateCountryCode();
        }
        this.selection.moveCursor(cursorPosition);
        this.softphone.shouldFocus = true;
    }

    /** @param {MouseEvent} ev */
    onClickCall(ev) {
        const inputValue = this.softphone.numpad.value.trim();
        if (!inputValue) {
            return;
        }
        this.userAgentService.makeCall({ phone_number: inputValue });
    }

    onClickKey(key) {
        this.onInputSearchBar();
        if (this.userAgentService.session?.sipSession) {
            this.userAgentService.session.sipSession.sessionDescriptionHandler.sendDtmf(key);
        }
        const value = this.softphone.numpad.value.trim();
        const { selectionStart, selectionEnd } = this.input.el;
        this.softphone.numpad.value =
            value.slice(0, selectionStart) + key + value.slice(selectionEnd);
        this.updateCountryCode();
        this.selection.moveCursor(selectionStart + 1);
        this.softphone.shouldFocus = true;
    }

    onClickFirstResult(contact) {
        this.userAgentService.makeCall({ partner: contact, phone_number: contact.phone });
    }

    onInputSearchBar(ev) {
        const searchTerms = this.softphone.numpad.value.trim();
        const isT9Code = [...searchTerms].every((letter) => letter in T9_MAPPING);
        this.voip.fetchContacts(searchTerms, 0, 30, isT9Code);
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
        if (this.userAgentService.session?.sipSession) {
            this.userAgentService.transfer(inputValue);
        } else {
            this.userAgentService.makeCall({ phone_number: inputValue });
        }
    }

    async updateCountryCode() {
        const phoneNumber = this.softphone.numpad.value.trim();
        // avoid making a request if the country code is already up to date
        if (this.phoneNumberStartsWithCountryCode) {
            return;
        }
        if (!phoneNumber.startsWith("00") && !phoneNumber.startsWith("+")) {
            return;
        }
        this.softphone.numpad.countryCode = await rpc("/voip/get_country_code", {
            phone_number: phoneNumber,
        });
    }
}

function normalize(str) {
    return unaccent(
        str
            .normalize("NFKD")
            .toLowerCase()
            .toUpperCase()
            .replaceAll("Œ", "OE")
            .replace(/\p{Diacritic}/gu, "")
    );
}

/**
 * @param {string} str
 * @param {string} substr
 * @returns {string} ⚠ markup
 */
export function highlightMatch(str, substr) {
    str = str.normalize("NFC");
    /**
     * Spreading strings into arrays ensures that we work on codepoints
     * (meaning, no unpaired surrogates and other shenanigans).
     *  [..."🪬"][0] === "🪬"   ← all good
     *  "🪬"[0] === "\ud83d"    ← broken
     */
    const codepoints = [...str];
    /**
     * Normalizing the array element by element ensures that the array doesn't
     * change in length after normalization.
     *
     * Example of a string that changes length after normalization:
     *  "ß".toUpperCase() === "SS"
     *
     * Keeping the same length is important because we need to know where the
     * match starts and ends in the original, unnormalized string in order to
     * highlight it.
     */
    const normalizedSrc = codepoints.map(normalize);
    const normalizedSubstr = [...normalize(substr)];
    const flattenSrcLength = [...normalizedSrc.join("")].length;
    let matchStart = -1;
    let matchLength = 0;
    outerLoop: for (let i = 0; i <= flattenSrcLength - normalizedSubstr.length; ++i) {
        const substringStack = normalizedSubstr.toReversed();
        for (let j = 0; i + j < normalizedSrc.length; ++j) {
            const str = normalizedSrc[i + j];
            for (const char of str) {
                if (substringStack.length < 1 || char !== substringStack.pop()) {
                    continue outerLoop;
                }
                if (substringStack.length === 0) {
                    matchStart = i;
                    matchLength = j + 1;
                    break outerLoop;
                }
            }
        }
    }
    if (matchStart === -1) {
        return "";
    }
    const before = codepoints.slice(0, matchStart).join("");
    const match = codepoints.slice(matchStart, matchStart + matchLength).join("");
    const after = codepoints.slice(matchStart + matchLength).join("");
    return markup`${before}<span class="fw-bolder">${match}</span>${after}`;
}

function highlightT9Match(name, t9) {
    t9 = [...t9].reverse();
    const nameAsArr = [...name];
    let matchEnd = 0;
    for (matchEnd = 0; matchEnd < nameAsArr.length; ++matchEnd) {
        if (t9.length < 1) {
            break;
        }
        const normalized = normalize(nameAsArr[matchEnd]).toUpperCase();
        // extra loop, in case normalizing generates more letters
        for (const char of normalized) {
            if (t9.length === 0) {
                return "";
            }
            const possibleLetters = T9_MAPPING[t9.pop()];
            if (!possibleLetters.includes(char)) {
                return "";
            }
        }
    }
    if (t9.length !== 0) {
        return "";
    }
    return htmlJoin(
        markup(`<span class="fw-bolder">`),
        ...nameAsArr.slice(0, matchEnd),
        markup("</span>"),
        ...nameAsArr.slice(matchEnd)
    );
}

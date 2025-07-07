import { normalize } from "@web/core/l10n/utils";

/**
 * Removes whitespaces, dashes, slashes and periods from a phone number.
 *
 * @param {string} phoneNumber
 * @returns {string}
 */
export function cleanPhoneNumber(phoneNumber) {
    // U+00AD is the “soft hyphen” character
    return phoneNumber.replace(/[-()\s/.\u00AD]/g, "");
}

export function isSubstring(targetString, substring) {
    if (!targetString) {
        return false;
    }
    return normalize(targetString).includes(normalize(substring));
}

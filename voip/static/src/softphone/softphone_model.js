import { KeypadModel } from "@voip/softphone/keypad_model";
import { isSubstring } from "@voip/utils/utils";

/**
 * Retains the state of the Softphone that needs to be persisted even if the
 * corresponding component is unmounted.
 */
export class Softphone {
    activeTab = "dialer";
    activeTabSection = "";
    activeRecord = null;
    dialer = new KeypadModel();
    isDisplayed = false;
    numpad = {
        isOpen: false,
        value: "",
        selection: {
            start: 0,
            end: 0,
            direction: "none",
        },
        countryCode: {
            iso: "",
            itu: "",
        },
    };
    addressBook = {
        searchInputValue: "",
    };
    agenda = {
        searchInputValue: "",
    };
    callSummary = {
        /**
         * @type {import("@voip/core/call_model").Call}
         */
        call: null,
        isShown: false,
        hideAfterTimeout: undefined,
        scrollToActiveRecord: false,
    };
    history = {
        searchInputValue: "",
    };
    inCallView = {
        keypad: {
            isOpen: false,
            state: new KeypadModel(),
        },
    };
    shouldFocus = false;

    constructor(store, voip) {
        this.store = store;
        this.voip = voip;
    }

    get activities() {
        const searchInputValue = this.agenda.searchInputValue.trim();
        return Object.values(this.store["mail.activity"].records).filter(
            (activity) =>
                activity.activity_category === "phonecall" &&
                ["today", "overdue"].includes(activity.state) &&
                activity.phone &&
                activity.user_id === this.store.self.userId &&
                (!searchInputValue ||
                    [
                        activity.partner.name,
                        activity.partner.displayName,
                        activity.phone,
                        activity.name,
                    ].some((x) => isSubstring(x, searchInputValue)))
        );
    }

    get contacts() {
        return Object.values(this.store.Persona.records).filter((persona) =>
            Boolean(persona.phone)
        );
    }

    hide() {
        this.isDisplayed = false;
    }

    hideCallSummary() {
        clearTimeout(this.callSummary.hideAfterTimeout);
        Object.assign(this.callSummary, {
            call: null,
            hideAfterTimeout: undefined,
            isShown: false,
        });
    }

    show() {
        this.isDisplayed = true;
        this.shouldFocus = true;
    }

    showSummary(call) {
        clearTimeout(this.callSummary.hideAfterTimeout);
        Object.assign(this.callSummary, {
            call,
            hideAfterTimeout: setTimeout(() => {
                this.hideCallSummary();
                this.callSummary.scrollToActiveRecord = true;
            }, 3000),
            isShown: true,
        });
    }
}

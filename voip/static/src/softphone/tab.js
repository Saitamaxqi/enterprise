import { useVisible } from "@mail/utils/common/hooks";

import { Component, useEffect, useRef } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Generic component that defines the general structure of a softphone tab.
 */
export class Tab extends Component {
    static defaultProps = {
        extraClass: "",
        getSectionStyle: (item) => "",
        hasSearchBar: true,
        noEntriesMessage: _t("Nothing to see here 😔"),
        onInputSearch: () => {},
        onTabEnd: () => {},
        sectionIcon: "",
    };
    static props = {
        extraClass: { type: String, optional: true },
        /**
         * Function that computes the additional classes to be applied to a
         * section name. It takes the first item of the section as an argument.
         */
        getSectionStyle: { type: Function, optional: true },
        hasSearchBar: { type: Boolean, optional: true },
        itemsBySection: Map,
        /**
         * Message displayed when there are no entries in the tab.
         */
        noEntriesMessage: { type: String, optional: true },
        noSearchResultsMessage: { type: String, optional: true },
        onClickBack: { type: Function, optional: true },
        onInputSearch: { type: Function, optional: true },
        /**
         * Function to be called each time the user scrolls to the end of the
         * tab. Useful to implement "load more" feature.
         */
        onTabEnd: { type: Function, optional: true },
        sectionIcon: { type: String, optional: true },
        slots: Object,
        state: Object,
    };
    static template = "voip.Tab";

    setup() {
        this.voip = useService("voip");
        this.softphone = this.voip.softphone;
        this.searchInput = useRef("searchInput");
        useVisible("end-of-tab", (isVisible) => {
            if (isVisible) {
                this.props.onTabEnd();
            }
        });
        useEffect(
            (shouldFocus) => {
                if (shouldFocus) {
                    if (this.searchInput.el && !this.voip.error) {
                        this.searchInput.el.focus();
                    }
                    this.softphone.shouldFocus = false;
                }
            },
            () => [this.softphone.shouldFocus]
        );
    }

    /**
     * When an RPC is pending, the search icon is replaced with a spinner.
     *
     * @returns {string}
     */
    get searchBarIcon() {
        if (this.voip.hasPendingRequest) {
            return "fa fa-spin fa-circle-o-notch";
        }
        return "oi oi-search";
    }

    onClickBack() {
        if (this.props.onClickBack) {
            this.props.onClickBack();
        }
    }
}

import { ActionButton } from "@voip/softphone/action_button";
import { NoSearchResults } from "@voip/softphone/no_search_results";
import { TabEntry } from "@voip/softphone/tab_entry";

export const tabComponents = { ActionButton, NoSearchResults, Tab, TabEntry };

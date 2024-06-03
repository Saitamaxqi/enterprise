/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { dragAndDropSignItemAtHeight } from "./sign_template_creation_tour";

registry.category("web_tour.tours").add("sign_indicator_tour", {
    url: "/odoo?debug=1",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Sign App",
            trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
            run: "click",
        },
        {
            content: "Click on Template Menu",
            trigger: 'a[data-menu-xmlid="sign.sign_template_menu"]',
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_last_breadcrumb_item > span:contains('Templates')",
        },
        {
            content: "Remove My Favorites filter",
            trigger: ".o_cp_searchview .o_facet_remove",
            run: "click",
        },
        {
            content: 'Search template "temp_template"',
            trigger: ".o_cp_searchview input",
            run: "fill temp_template",
        },
        {
            content: "Search Document Name",
            trigger: ".o_searchview_autocomplete .o-dropdown-item:first",
            run: "click",
        },
        {
            content: "Enter Template Edit Mode",
            trigger: '.o_sign_kanban_card_ungrouped:first span:contains("temp_template")',
            run: "click",
        },
        {
            content: "Wait for iframe to load PDF",
            trigger: ":iframe #viewerContainer",
        },
        {
            content: "Wait for page to be loaded",
            trigger: ":iframe .page",
        },
        {
            content: "Drop Signature Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Signature)",
            run: function () {
                dragAndDropSignItemAtHeight(this.anchor, 1, 0.5, 0.25);
            },
        },
        {
            trigger: ".o_sign_status_indicator .o_sign_button_save",
            run: "click",
        },
        {
            content: "Drop Name Sign Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Name)",
            run: function () {
                dragAndDropSignItemAtHeight(this.anchor, 1, 0.25, 0.25);
            },
        },
        {
            trigger: ".o_sign_status_indicator .o_sign_button_cancel",
            run: "click",
        },
        {
            content: "Wait for discarding changes",
            trigger: ".o_sign_status_indicator .o_sign_button_saved",
        },
        {
            content: "Drop Selection Sign Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Selection)",
            run: function () {
                dragAndDropSignItemAtHeight(this.anchor, 1, 0.75, 0.25);
            },
        },
        {
            content: "Open popover on Selection sign item",
            trigger: ':iframe .o_sign_sign_item:contains("Selection") .o_sign_item_display',
            run: "click",
        },
        {
            trigger: ".breadcrumb .o_back_button",
            run: "click",
        },
    ],
});

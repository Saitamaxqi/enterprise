/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add("rental_cart_update_duration", {
    url: "/shop",
    steps: () => [
        {
            content: "Search computer write text",
            trigger: 'form input[name="search"]',
            run: "edit computer",
        },
        {
            content: "Search computer click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
            run: "click",
        },
        {
            content: "Select computer",
            trigger: '.oe_product_cart:first a:contains("Computer")',
            run: "click",
        },
        {
            content: "Wait computer informations are loaded",
            trigger: "img.product_detail_img[src*='Computer']",
        },
        {
            content: "Open daterangepicker",
            trigger: "input[name=renting_start_date]",
            run: "click",
        },
        {
            content: "Wait for the datepicker to be opened",
            trigger: ".o_time_picker_input",
            run: "click",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_input:eq(0)",
            run: "edit 6:00 && press Enter",
        },
        {
            content: "Pick end time",
            trigger: ".o_time_picker_input:eq(1)",
            run: "edit 12:00 && press Enter",
        },
        {
            content: "click on add to cart",
            trigger:
                '#product_detail form #add_to_cart',
            run: "click",
        },
        tourUtils.goToCart(),
        {
            content: "Verify Rental Product is in the cart",
            trigger: '#cart_products div div.css_quantity input[value="1"]',
        },
        {
            content: "Open daterangepicker",
            trigger: "input[name=renting_start_date]",
            run: "click",
        },
        {
            content: "Wait for the datepicker to be opened",
            trigger: ".o_time_picker_input",
            run: "click",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_input:eq(0)",
            run: "edit 8:00 && press Enter && press Escape",
        },
        {
            content: "Verify order line rental period start time",
            trigger: 'div.text-muted.small span:contains("08:00")',
        },
        {
            content: "Verify order line rental period return time",
            trigger: 'div.text-muted.small span:contains("12:00")',
        },
    ],
});

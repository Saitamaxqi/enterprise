import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_operation_quality_check_barcode", {
    steps: () => [
        {
            trigger: ".o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_barcode_picking_type:contains(Receipts)",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product1",
        },
        {
            trigger: ".fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_digipad_increment",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run() {},
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product2",
        },
        {
            trigger:
                ".o_barcode_line:has(.o_barcode_line_title:contains(product2)) button.o_add_quantity",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 1)) button[name=do_pass]",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 2)) button[name=do_fail]",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("test_operation_quality_check_delivery_barcode", {
    steps: () => [
        {
            trigger: ".o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('Delivery')",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product1",
        },
        {
            trigger: ".fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_digipad_increment",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run() {},
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product2",
        },
        {
            trigger:
                ".o_barcode_line:has(.o_barcode_line_title:contains(product2)) button.o_add_quantity",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 1)) button[name=do_pass]",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 2)) button[name=do_fail]",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run() {},
        },
    ],
});

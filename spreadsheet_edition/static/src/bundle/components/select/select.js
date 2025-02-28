import { Component } from "@odoo/owl";

export class Select extends Component {
    static template = "spreadsheet_edition.Select";
    static components = {};
    static props = {
        value: { type: String, optional: true },
        class: { type: String, optional: true },
        options: {
            type: Array,
            element: {
                type: Object,
                shape: { value: String, description: String },
            },
        },
        onOptionSelected: Function,
    };
}

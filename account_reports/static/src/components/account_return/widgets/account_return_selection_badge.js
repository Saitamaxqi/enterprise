import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cookie } from "@web/core/browser/cookie";

export class AccountReturnSelectionBadge extends Component {
    static template = "account_reports.AccountReturnSelectionBadgeField";
    static props = {
        ...standardFieldProps,
        decorations: { type: Object, optional: true },
        options: { type: Object, optional: true },
        class: { type: String, optional: true },
        size: { type: String, optional: true },
    };

    static defaultProps = {
        size: "normal"
    };

    static components = {
        Dropdown,
        DropdownItem,
    }

    get options() {
        return this.props.record.fields[this.props.name].selection;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get required() {
        return this.props.record.fields[this.props.name].required;
    }

    get display() {
        const result = this.options.filter((val) => val[0] == this.value)[0];
        if(result) {
            return result[1];
        }
        return null;
    }

    decorationForValue(value, isDropdownItem=false) {
        const colorScheme = cookie.get("color_scheme");
        const default_style = isDropdownItem && colorScheme == 'dark' ? "text-bg-200" : "text-bg-300";
        const decoration = this.props.options[value];
        if (decoration) {
            if (decoration === "muted") {
                return default_style;
            }
            return `text-bg-${this.props.options[value]}`;
        }
        return default_style;
    }

    get additionalClassName() {
        return this.props.class;
    }

    get capsuleStyle() {
        if (this.props.size === 'normal') {
            return "min-width: 70px; height:21px;";
        }
        else {
            return "";
        }
    }

    onChange(value) {
        this.props.record.update(
            { [this.props.name]: value },
            { save: true }
        );
    }
}

export const accountReturnSelectionBadge = {
    supportedTypes: ["selection"],
    component: AccountReturnSelectionBadge,
    extractProps: ({options}) => {
        return { options };
    },
}

registry.category("fields").add("account_return_selection_badge", accountReturnSelectionBadge)

/** @ts-check */

import { stores, components } from "@odoo/o-spreadsheet";
import { onWillStart, Component } from "@odoo/owl";
import { FilterEditorStore } from "../../filter_editor_store";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";

const { Checkbox, Section, SidePanelCollapsible, TextInput } = components;
const { useLocalStore } = stores;

/**
 * @typedef {import("@spreadsheet").OdooField} OdooField
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 *
 * @typedef State
 * @property {boolean} saved
 * @property {string} label label of the filter
 */

/**
 * This is the side panel to define/edit a global filter.
 * It can be of 3 different type: text, date and relation.
 */
export class AbstractFilterEditorSidePanel extends Component {
    static template = "";
    static components = {
        SidePanelCollapsible,
        Checkbox,
        Section,
        TextInput,
        FilterEditorFieldMatching,
    };
    static props = {
        id: { type: String, optional: true },
        label: { type: String, optional: true },
        fieldMatching: { type: Object, optional: true },
        onCloseSidePanel: { type: Function, optional: true },
    };

    setup() {
        this.store = useLocalStore(FilterEditorStore, this.props, this.type);
        onWillStart(async () => await this.store.loadData);
    }

    get type() {
        throw new Error("Not implemented by children");
    }

    /**
     * @param {String} label
     */
    setLabel(label) {
        this.store.update({ label });
    }

    updateDefaultValue(defaultValue) {
        if (Array.isArray(defaultValue) && defaultValue.length === 0) {
            this.store.update({ defaultValue: undefined });
        } else {
            this.store.update({ defaultValue });
        }
    }

    /**
     * Function that will be called by ModelFieldSelector on each fields, to
     * filter the ones that should be displayed
     * @param {OdooField} field
     * @param {string} path
     * @param {[string]} coModel Only set when the filter is relation
     * @returns {boolean}
     */
    filterModelFieldSelectorField(field, path, coModel) {
        if (!field.searchable) {
            return false;
        }
        if (field.name === "id" && this.type === "relation") {
            const paths = path.split(".");
            const lastField = paths.at(-2);
            if (!lastField || (lastField.relation && lastField.relation === coModel)) {
                return true;
            }
            return false;
        }
        return this.store.allowedFieldTypes.includes(field.type) || !!field.relation;
    }

    sortModelFieldSelectorFields(fields) {
        return Object.keys(fields).sort((a, b) => {
            if (fields[a].relation && fields[b].relation) {
                return fields[a].string.localeCompare(fields[b].string);
            }
            if (fields[a].relation) {
                return 1;
            }
            if (fields[b].relation) {
                return -1;
            }
            return fields[a].string.localeCompare(fields[b].string);
        });
    }

    onSave() {
        this.store.saveGlobalFilter();
    }

    onCancel() {
        this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
    }

    onDelete() {
        if (this.props.id) {
            this.env.model.dispatch("REMOVE_GLOBAL_FILTER", { id: this.props.id });
        }
        this.env.openSidePanel("GLOBAL_FILTERS_SIDE_PANEL", {});
    }
}

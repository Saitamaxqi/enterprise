/** @ts-check */

import { ModelSelector } from "@web/core/model_selector/model_selector";
import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { useService } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { components } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

import { useState, onWillStart } from "@odoo/owl";
import { SidePanelDomain } from "../../../components/side_panel_domain/side_panel_domain";

const { ValidationMessages } = components;

/**
 * @typedef {import("@spreadsheet").OdooField} OdooField
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 */

/**
 * This is the side panel to define/edit a global filter of type "relation".
 */
export class RelationFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.RelationFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        ModelSelector,
        MultiRecordSelector,
        FilterEditorFieldMatching,
        SidePanelDomain,
        ValidationMessages,
    };
    static props = {
        ...AbstractFilterEditorSidePanel.props,
        modelName: { type: String, optional: true },
        modelDisplayName: { type: String, optional: true },
    };
    setup() {
        super.setup();

        this.state = useState({
            domainRestriction: this.store.filter.domainOfAllowedValues?.length > 0,
        });

        this.nameService = useService("name");
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
    }

    get type() {
        return "relation";
    }

    get missingModel() {
        return !this.store.filter.modelName;
    }

    async onWillStart() {
        const promises = [this.fetchRelationModelLabel()];
        if (!this.store.canUseChildOf) {
            promises.push(this.computeCanUseChildOf());
        }
        await Promise.all(promises);
    }

    get invalidModel() {
        return _t(
            "At least one data source has an invalid model. Please delete it before editing this global filter."
        );
    }

    async onModelSelected({ technical, label }) {
        this.store.selectRelatedModel(technical, label);
        await this.computeCanUseChildOf();
        this.store.update({ includeChildren: this.store.canUseChildOf });
    }

    async fetchRelationModelLabel() {
        if (!this.store.filter.modelName) {
            return;
        }
        const result = await this.orm
            .cached()
            .call("ir.model", "display_name_for", [[this.store.filter.modelName]]);
        const label = result[0]?.display_name;
        this.store.updateRelationModelLabel(label);
        if (!this.store.filter.label) {
            this.store.update({ label });
        }
    }

    async computeCanUseChildOf() {
        if (!this.store.filter.modelName) {
            this.store.updateCanUseChildOf(false);
            return;
        }
        const hasParentRelation = await this.orm.call(
            "ir.model",
            "has_searchable_parent_relation",
            [this.store.filter.modelName]
        );
        this.store.updateCanUseChildOf(hasParentRelation);
    }

    /**
     * @param {Number[]} value
     */
    async onValuesSelected(resIds) {
        const displayNames = await this.nameService.loadDisplayNames(
            this.store.filter.modelName,
            resIds
        );
        this.store.update({
            defaultValue: resIds.length ? resIds : undefined,
            displayNames: Object.values(displayNames),
        });
    }

    toggleDefaultsToCurrentUser(checked) {
        if (checked) {
            this.store.update({ defaultValue: "current_user" });
        } else {
            this.store.update({ defaultValue: undefined });
        }
    }
    toggleDomainRestriction(isChecked) {
        if (!isChecked) {
            this.onDomainUpdate([]);
        }
        this.state.domainRestriction = isChecked;
    }

    onDomainUpdate(domainOfAllowedValues) {
        this.store.update({ domainOfAllowedValues });
    }
}

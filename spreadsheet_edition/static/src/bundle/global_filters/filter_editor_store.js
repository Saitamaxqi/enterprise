import { stores, helpers } from "@odoo/o-spreadsheet";
import { ModelNotFoundError } from "@spreadsheet/data_sources/data_source";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { globalFieldMatchingRegistry } from "@spreadsheet/global_filters/helpers";

const { UuidGenerator } = helpers;

const { SpreadsheetStore, NotificationStore, SidePanelStore } = stores;

export class FilterEditorStore extends SpreadsheetStore {
    mutators = [
        "saveGlobalFilter",
        "selectRelatedModel",
        "update",
        "updateCanUseChildOf",
        "updateFieldMatching",
        "updateFieldMatchingOffset",
        "updateRelationModelLabel",
    ];

    constructor(get, initialProps, type, orm, fieldService) {
        super(get);
        this.isNew = !initialProps.id;
        this.filterId = initialProps.id || new UuidGenerator().smallUuid();
        if (this.isNew) {
            this.draft = {
                id: this.filterId,
                label: initialProps.label ?? "",
                type,
            };
        }
        this._allModelsExist = false;
        this.missingLabelError = false; // Only set to true when the user tries to update the filter without the label
        this.notificationStore = this.get(NotificationStore);
        this.sidePanelStore = this.get(SidePanelStore);
        this.loadDataPromise = this._loadData(initialProps);
        this._canUseChildOf = this.filter.includeChildren;
        this._fieldsMatching = [];
        this._relationModelLabel = "";
    }

    get allowedFieldTypes() {
        switch (this.filter.type) {
            case "text":
                return ["char", "text", "many2one"];
            case "date":
                return ["date", "datetime"];
            case "boolean":
                return ["boolean"];
            case "relation":
                return ["many2one", "many2many", "one2many"];
        }
        return [];
    }

    get canSave() {
        return (
            (this.filter.type !== "relation" || this.filter.modelName) &&
            this.fieldsMatching.every((fm) => fm.isValid)
        );
    }

    get canUseChildOf() {
        return this.filter.type === "relation" && this._canUseChildOf;
    }

    get evaluatedDomain() {
        const domain = this.filter.domainOfAllowedValues;
        if (!domain) {
            return [];
        }
        return new Domain(domain).toList(user.context);
    }

    get fieldsMatching() {
        return this._fieldsMatching;
    }

    get filter() {
        return (
            this.draft || {
                ...this.getters.getGlobalFilter(this.filterId),
                label: _t(this.getters.getGlobalFilter(this.filterId).label),
            }
        );
    }

    get isResUserRelation() {
        return this.filter.modelName === "res.users";
    }

    get isValid() {
        return this._allModelsExist;
    }

    get labelPlaceholder() {
        return _t("New %s filter", this.filter.type);
    }

    get loadData() {
        return this.loadDataPromise;
    }

    get rangesForSelectionInput() {
        const range = this.filter.rangesOfAllowedValues;
        if (!range) {
            return [];
        }
        const sheetId = this.getters.getActiveSheetId();
        return this.filter.rangesOfAllowedValues.map((range) =>
            this.getters.getRangeString(range, sheetId)
        );
    }

    get relationModelLabel() {
        return this._relationModelLabel;
    }

    get shouldDisplayFieldMatching() {
        switch (this.filter.type) {
            case "text":
            case "date":
            case "boolean":
                return this._fieldsMatching.length;
            case "relation":
                return this._fieldsMatching.length && this.filter.modelName;
        }
        return false;
    }

    get textOptions() {
        if (!this.filter.rangesOfAllowedValues) {
            return [];
        }
        return this.getters.getTextFilterOptionsFromRanges(
            this.filter.rangesOfAllowedValues,
            this.filter.defaultValue
        );
    }

    selectRelatedModel(technical, label) {
        if (this.filter.type !== "relation") {
            return;
        }
        if (!this.filter.label) {
            this.update({ label });
        }
        if (this.filter.modelName !== technical) {
            this.update({ defaultValue: undefined });
        }
        this.update({ modelName: technical, domainOfAllowedValues: [] });
        this.updateRelationModelLabel(label);

        this.fieldsMatching.forEach((fm) => {
            const field = this._findRelation(fm.model(), fm.fields());
            this.updateFieldMatching(fm.id, field ? field.name : undefined, field);
        });
    }

    update(update) {
        this.draft = { ...this.filter, ...this.draft, ...update };
        if (!this.draft.label) {
            this.missingLabelError = true;
        }
    }

    updateCanUseChildOf(canUseChildOf) {
        this._canUseChildOf = canUseChildOf;
    }

    updateRelationModelLabel(label) {
        this._relationModelLabel = label;
    }

    updateFieldMatching(id, chain, field) {
        const fieldMatch = this.fieldsMatching.find((fm) => fm.id === id);
        if (!fieldMatch) {
            return;
        }
        if (!chain) {
            fieldMatch.isValid = true;
            fieldMatch.fieldMatch = {};
            return;
        }
        if (!field) {
            fieldMatch.isValid = false;
        }
        const fieldName = chain;
        fieldMatch.fieldMatch = {
            chain: fieldName,
            type: field?.type || "",
        };
        if (
            !field ||
            (field.name !== "id" && !this._matchingRelation(field)) ||
            !field.searchable
        ) {
            fieldMatch.isValid = false;
        } else {
            fieldMatch.isValid = true;
        }
        this.draft = this.filter;
    }

    updateFieldMatchingOffset(id, offset) {
        const fieldMatch = this._fieldsMatching.find((fm) => fm.id === id);
        if (!fieldMatch) {
            return;
        }
        fieldMatch.fieldMatch.offset = offset;
        this.draft = this.filter;
    }

    saveGlobalFilter() {
        if (!this.canSave) {
            return;
        }
        if (!this.draft) {
            this.sidePanelStore.open("GLOBAL_FILTERS_SIDE_PANEL");
            return;
        }
        let filter = this.draft;
        if (filter.rangesOfAllowedValues) {
            // rangesOfAllowedValues is an array of RangeData in the command
            filter = {
                ...filter,
                rangesOfAllowedValues: filter.rangesOfAllowedValues.map((range) =>
                    this.getters.getRangeData(range)
                ),
            };
        }
        const command = this.isNew ? "ADD_GLOBAL_FILTER" : "EDIT_GLOBAL_FILTER";
        const result = this.model.dispatch(command, {
            filter,
            ...this._getFieldsMatchingPayload(),
        });
        if (result.isCancelledBecause(CommandResult.DuplicatedFilterLabel)) {
            this.notificationStore.raiseError(_t("Duplicated filter label"));
        } else {
            this.draft = undefined;
            this.sidePanelStore.open("GLOBAL_FILTERS_SIDE_PANEL");
        }
    }

    async _loadData({ modelName, modelDisplayName, fieldMatching } = {}) {
        this._allModelsExist = await this._waitForDataSourcesBeReady();
        if (this.isNew && this.filter.type === "relation" && modelName) {
            this.selectRelatedModel(modelName, modelDisplayName);
        }
        await this._loadFilterMatchings(fieldMatching);
    }

    async _waitForDataSourcesBeReady() {
        try {
            const promises = globalFieldMatchingRegistry
                .getAll()
                .map((el) => el.waitForReady(this.model.getters))
                .flat();
            await Promise.all(promises);
        } catch (e) {
            if (e instanceof ModelNotFoundError) {
                console.error(e);
                return false;
            } else {
                throw e;
            }
        }
        return true;
    }

    async _loadFilterMatchings(initialFieldMatching = {}) {
        let id = 0;
        for (const type of globalFieldMatchingRegistry.getKeys()) {
            const el = globalFieldMatchingRegistry.get(type);
            for (const dataSourceId of el.getIds(this.model.getters)) {
                const model = el.getModel(this.model.getters, dataSourceId);
                const tag = await el.getTag(this.model.getters, dataSourceId);
                this._fieldsMatching.push({
                    id,
                    name: el.getDisplayName(this.model.getters, dataSourceId),
                    tag,
                    fieldMatch:
                        initialFieldMatching[model] ||
                        el.getFieldMatching(this.model.getters, dataSourceId, this.filterId) ||
                        {},
                    fields: () => el.getFields(this.model.getters, dataSourceId),
                    model: () => model,
                    payload: () => ({ id: dataSourceId, type }),
                    isValid: true,
                });
                id++;
            }
        }
    }

    /**
     * Get the first field which could be a relation of the current related
     * model
     *
     * @param {string} model
     * @param {Object.<string, OdooField>} fields Fields to look in
     * @returns {OdooField|undefined}
     */
    _findRelation(model, fields) {
        if (this.filter.modelName === model) {
            return Object.values(fields).find((field) => field.name === "id");
        }
        const field = Object.values(fields).find(
            (field) => field.searchable && field.relation === this.filter.modelName
        );
        return field;
    }

    /**
     * Compute the fields matching data that should be sent through the command
     */
    _getFieldsMatchingPayload() {
        const fieldMatchings = {};
        [...this.fieldsMatching].forEach((fm) => {
            const { type, id } = fm.payload();
            fieldMatchings[type] = fieldMatchings[type] || {};
            fieldMatchings[type][id] = fm.fieldMatch;
        });
        return fieldMatchings;
    }

    _matchingRelation(field) {
        return this.filter.type === "relation"
            ? field.relation === this.filter.modelName
            : !field.relation;
    }
}

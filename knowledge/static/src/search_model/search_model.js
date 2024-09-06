/** @odoo-module **/

import { SearchModel } from "@web/search/search_model";

export const KnowledgeSearchModelMixin = (T) => class extends T {
    setup(services, args) {
        this.saveEmbeddedViewFavoriteFilter = args.saveEmbeddedViewFavoriteFilter;
        this.deleteEmbeddedViewFavoriteFilter = args.deleteEmbeddedViewFavoriteFilter;
        super.setup(services, args);
    }

    /**
     * Favorites for embedded views
     * @override
     */
    async load(config) {
        await super.load(config);
        if (config.state && !this.isStateCompleteForEmbeddedView) {
            // If the config contains an imported state that is not directly
            // coming from a view that was embedded in Knowledge, the favorite
            // filters have to be loaded, since they come from the
            // `data-embedded-props` attribute of the anchor for the
            // EmbeddedViewComponent. Otherwise, those are already specified in
            // the state and they should not be duplicated.
            let defaultFavoriteId = null;
            const activateFavorite = "activateFavorite" in config ? config.activateFavorite : true;
            if (activateFavorite) {
                defaultFavoriteId = this._createGroupOfFavorites(this.irFilters || []);
                if (defaultFavoriteId) {
                    // activate default search items (populate this.query)
                    this._activateDefaultSearchItems(defaultFavoriteId);
                }
            }
        }
    }

    /**
     * Save in embedded view arch instead of creating a record
     * @override
     */
    async _createIrFilters(irFilter) {
        this.saveEmbeddedViewFavoriteFilter(irFilter);
        return null;
    }

    /**
     * Delete from the embedded view arch instead of deleting the record
     * @override
     */
    async _deleteIrFilters(searchItem) {
        this.deleteEmbeddedViewFavoriteFilter(searchItem);
    }

    /**
     * @override
     * @returns {Object}
     */
    exportState() {
        const state = super.exportState();
        state.isStateCompleteForEmbeddedView = true;
        return state;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(state);
        this.upgradeEmbedFilters();
        this.isStateCompleteForEmbeddedView = state.isStateCompleteForEmbeddedView;
    }

    /**
     * Upgrade the old generator ids for dateFilters to the new system.
     * TODO ABD: remove this function once the upgrade procedure for knowledge
     * articles has been decided.
     */
    upgradeEmbedFilters() {
        // dateFilter generatorIds upgrade mapping
        const dfOptMap = {
            this_year: "year",
            last_year: "year-1",
            antepenultimate_year: "year-2",
            this_month: "month",
            last_month: "month-1",
            antepenultimate_month: "month-2",
        };
        for (const searchItem of Object.values(this.searchItems)) {
            if (searchItem.type === "dateFilter") {
                const newDefaults = new Set();
                for (const generatorId of searchItem.defaultGeneratorIds) {
                    if (generatorId in dfOptMap) {
                        newDefaults.add(dfOptMap[generatorId]);
                    }
                }
                if (newDefaults.size) {
                    searchItem.defaultGeneratorIds = Array.from(newDefaults);
                }
                if (!searchItem.optionsParams) {
                    searchItem.optionsParams = {
                        startYear: -2,
                        endYear: 0,
                        startMonth: -2,
                        endMonth: 0,
                        customOptions: [],
                    }
                }
                for (const queryItem of this.query) {
                    if (
                        queryItem.searchItemId === searchItem.id &&
                        queryItem.generatorId &&
                        queryItem.generatorId in dfOptMap
                    ) {
                        queryItem.generatorId = dfOptMap[queryItem.generatorId];
                    }
                }
            }
        }
    }
};

export class KnowledgeSearchModel extends KnowledgeSearchModelMixin(SearchModel) {}

import { SearchModel } from "@web/search/search_model";
import { patch } from "@web/core/utils/patch";

const CHAR_FIELDS = ["char", "html", "many2many", "many2one", "one2many", "text", "properties"];

patch(SearchModel.prototype, {
    async load(config) {
        const result = await super.load(config);
        if (config.ai) {
            // TODO JCB: support dateGroupBy and fieldProperty
            // TODO JCB: name vs fieldName, which one to use?
            for (const filter of config.ai.selectedFilters || []) {
                const [searchItem] = this.getSearchItems(
                    (i) => i.type === "filter" && [i.name, i.fieldName].includes(filter)
                );
                if (searchItem && !searchItem?.isActive) {
                    this.toggleSearchItem(searchItem.id);
                }
            }
            for (const groupBy of config.ai.selectedGroupBys || []) {
                const [searchItem] = this.getSearchItems(
                    (i) => i.type === "groupBy" && [i.name, i.fieldName].includes(groupBy)
                );

                if (searchItem && !searchItem?.isActive) {
                    this.toggleSearchItem(searchItem.id);
                }
            }
            if (config.ai.search && config.ai.search.length > 0) {
                for (const searchString of config.ai.search) {
                    const separatorIndex = searchString.indexOf("=");
                    if (separatorIndex === -1) {
                        console.warn(
                            `Invalid search format: "${searchString}". Expected format: "field=text"`
                        );
                        continue;
                    }
                    const fieldName = searchString.substring(0, separatorIndex);
                    const value = searchString.substring(separatorIndex + 1);

                    const [searchItem] = this.getSearchItems(
                        (i) => i.type === "field" && i.fieldName === fieldName
                    );
                    if (searchItem && !searchItem.isActive) {
                        this.addAutoCompletionValues(searchItem.id, {
                            value,
                            label: value,
                            operator:
                                searchItem.operator ||
                                (CHAR_FIELDS.includes(searchItem.fieldType) ? "ilike" : "="),
                        });
                    }
                }
            }
            if (config.ai.customDomain) {
                await this.splitAndAddDomain(config.ai.customDomain);
            }
        }
        return result;
    },
});

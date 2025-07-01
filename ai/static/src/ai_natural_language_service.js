import { registry } from "@web/core/registry";

export const aiNaturalLanguageService = {
    dependencies: ["bus_service", "action", "menu"],
    start(env, { bus_service, action: actionService, menu: menuService }) {
        bus_service.subscribe(
            "AI_OPEN_MENU_LIST",
            async ({ menuID, selectedFilters, selectedGroupBys, search, customDomain }) => {
                const menu = await menuService.getMenu(menuID);
                if (!menu.actionID) {
                    return;
                }
                const aiProps = { selectedFilters, selectedGroupBys, search };
                if (customDomain) {
                    aiProps.customDomain = customDomain;
                }
                await actionService.doAction(menu.actionID, {
                    props: { ai: aiProps },
                    viewType: "list",
                });
            }
        );
        bus_service.subscribe(
            "AI_OPEN_MENU_KANBAN",
            async ({ menuID, selectedFilters, selectedGroupBys, search, customDomain }) => {
                const menu = await menuService.getMenu(menuID);
                if (!menu.actionID) {
                    return;
                }
                const aiProps = { selectedFilters, selectedGroupBys, search };
                if (customDomain) {
                    aiProps.customDomain = customDomain;
                }
                await actionService.doAction(menu.actionID, {
                    props: { ai: aiProps },
                    viewType: "kanban",
                });
            }
        );
        bus_service.subscribe(
            "AI_OPEN_MENU_PIVOT",
            async ({
                menuID,
                selectedFilters,
                rowGroupBys,
                colGroupBys,
                measures,
                search,
                sortedColumn,
                customDomain,
            }) => {
                const menu = await menuService.getMenu(menuID);
                if (!menu.actionID) {
                    return;
                }
                const aiProps = {
                    selectedFilters,
                    selectedGroupBys: rowGroupBys,
                    colGroupBys,
                    measures,
                    search,
                };
                if (sortedColumn) {
                    aiProps.sortedColumn = sortedColumn;
                }
                if (customDomain) {
                    aiProps.customDomain = customDomain;
                }
                await actionService.doAction(menu.actionID, {
                    props: { ai: aiProps },
                    viewType: "pivot",
                });
            }
        );
        bus_service.subscribe(
            "AI_OPEN_MENU_GRAPH",
            async ({
                menuID,
                selectedFilters,
                groupBys,
                measure,
                mode,
                order,
                stacked,
                cumulated,
                search,
                customDomain,
            }) => {
                const menu = await menuService.getMenu(menuID);
                if (!menu.actionID) {
                    return;
                }
                const aiProps = {
                    selectedFilters,
                    groupBys,
                    measure,
                    mode,
                    order,
                    stacked,
                    cumulated,
                    search,
                };
                if (customDomain) {
                    aiProps.customDomain = customDomain;
                }
                await actionService.doAction(menu.actionID, {
                    props: { ai: aiProps },
                    viewType: "graph",
                });
            }
        );
        bus_service.start();
    },
};

registry.category("services").add("ai_natural_language_service", aiNaturalLanguageService);

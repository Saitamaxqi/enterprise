import { fields } from "@web/../tests/web_test_helpers";
import {
    SpreadsheetModels,
    defineSpreadsheetModels,
    getBasicServerData,
} from "@spreadsheet/../tests/helpers/data";
import {
    SpreadsheetDashboard as SpreadsheetDashboardCommunity,
    SpreadsheetDashboardGroup,
} from "@spreadsheet_dashboard/../tests/helpers/data";

export class SpreadsheetDashboard extends SpreadsheetDashboardCommunity {
    is_from_data = fields.Boolean({
        string: "Is from Data",
        default: false,
    });
}

export function defineSpreadsheetDashboardEditionModels() {
    const SpreadsheetDashboardModels = [SpreadsheetDashboard, SpreadsheetDashboardGroup];
    Object.assign(SpreadsheetModels, SpreadsheetDashboardModels);
    defineSpreadsheetModels();
}

export function getDashboardBasicServerData() {
    const { views, models } = getBasicServerData();
    return {
        views,
        models: { ...models, "spreadsheet.dashboard": { records: SpreadsheetDashboard._records } },
    };
}

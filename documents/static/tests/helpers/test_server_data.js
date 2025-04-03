import { getDocumentsTestServerData } from "@documents/../tests/helpers/data";

export const embeddedActionsServerData = getDocumentsTestServerData([
    {
        folder_id: 1,
        id: 2,
        name: "Request 1",
        available_embedded_actions_ids: [1],
    },
    {
        folder_id: 1,
        id: 3,
        name: "Request 2",
        available_embedded_actions_ids: [2, 3],
    },
    {
        folder_id: 1,
        id: 4,
        name: "Request 3",
        available_embedded_actions_ids: [3],
    },
]);
embeddedActionsServerData.models["ir.embedded.actions"] = {
    records: [
        { id: 1, name: "Action 1" },
        { id: 2, name: "Action 2 only" },
        { id: 3, name: "Action 2 and 3"},
    ],
};

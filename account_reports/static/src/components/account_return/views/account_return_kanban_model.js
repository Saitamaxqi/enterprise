import { RelationalModel } from "@web/model/relational_model/relational_model";

export class AccountReturnKanbanModel extends RelationalModel {
    static MAX_NUMBER_OPENED_GROUPS = Number.MAX_SAFE_INTEGER;

    setup() {
        super.setup(...arguments);
    }
}

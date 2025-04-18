import { RelationalModel } from "@web/model/relational_model/relational_model";

export class AccountReturnKanbanModel extends RelationalModel {
    setup() {
        super.constructor.MAX_NUMBER_OPENED_GROUPS = Number.MAX_SAFE_INTEGER;
        super.setup(...arguments);
    }
}

import { RelationalModel } from "@web/model/relational_model/relational_model";


export class AccountReturnKanbanModel extends RelationalModel {

    setup(params) {
        super.setup(...arguments);
        this.chatter = params.chatter;
    }

    async load(params={}) {
        await super.load(params);
        if (this.chatter) {
            // Reload the chatter when the changes are applied on the record
            this.env.bus.trigger("MAIL:RELOAD-THREAD", {
                model: "account.return",
                id: this.chatter.returnId,
            });
        }
    }
}

import { KanbanRecord } from "@web/views/kanban/kanban_record";


export class AccountReturnKanbanRecord extends KanbanRecord {

    static props = [
        ...KanbanRecord.props,
        "chatterState",
    ]

    setup() {
        super.setup();
    }

    getRecordClasses() {
        let classes = super.getRecordClasses().replace("flex-grow-1", "");

        if (this.props.chatterState.visible) {
            classes += " returns_chatter_visible";
            if (this.props.record.resId === this.props.chatterState.returnId) {
                classes += " account_return_selected";
            }
        }
        return classes
    }
}

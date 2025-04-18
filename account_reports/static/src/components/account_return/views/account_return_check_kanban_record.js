import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class AccountReturnCheckKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
    }
    
    onGlobalClick(ev, newWindow) {
        if (this.props.record.data.action)
            super.onGlobalClick(ev, newWindow);
    }
    
    getRecordClasses() {
        const { archInfo, forceGlobalClick } = this.props;
        const classes = ["o_kanban_record d-flex"];

        if ((forceGlobalClick || archInfo.openAction || archInfo.canOpenRecords) && this.props.record.data.action) {
            classes.push("cursor-pointer");
        }
        if (!this.props.groupByField) {
            classes.push("flex-grow-1 flex-md-shrink-1 flex-shrink-0");
        }
        classes.push(archInfo.cardClassName);
        return classes.join(" ");
    }
} 

import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { HelpdeskTicketGroupConfigMenu } from "../helpdesk_ticket_group_config_menu";

export class HelpdeskTicketKanbanHeader extends KanbanHeader {
    static components = {
        ...KanbanHeader.components,
        GroupConfigMenu: HelpdeskTicketGroupConfigMenu,
    };
}

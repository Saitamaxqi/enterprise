import { ListRenderer } from '@web/views/list/list_renderer';
import { HelpdeskTicketGroupConfigMenu } from '../helpdesk_ticket_group_config_menu';

export class HelpdeskTicketListRenderer extends ListRenderer {
    static components = {
        ...ListRenderer.components,
        GroupConfigMenu: HelpdeskTicketGroupConfigMenu,
    };

    get canCreateGroup() {
        return super.canCreateGroup && !!this.props.list.context.default_team_id;
    }
}

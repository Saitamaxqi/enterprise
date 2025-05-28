import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { Component } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";

export class SettingDocumentPermissionWidget extends Component {
    static template = 'documents_hr.SettingDocumentPermissionWidget';
    static props = { ...standardWidgetProps };

    setup() {
        this.documentService = useService("document.document");
    }

    async _openPermissionPanel() {
        const folder = this.props.record.data.documents_employee_folder_id;
        await this.documentService.openSharingDialog([folder.id]);
    }
}


export const hrDocumentSettingPermissionPanel = {
    component: SettingDocumentPermissionWidget,
};

registry.category('view_widgets').add('hr_document_setting_permission_widget', hrDocumentSettingPermissionPanel);

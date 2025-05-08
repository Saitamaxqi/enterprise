import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { DocumentsPermissionPanel } from "@documents/components/documents_permission_panel/documents_permission_panel";
import { Component } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";

export class SettingDocumentPermissionWidget extends Component {
    static template = 'documents_hr.SettingDocumentPermissionWidget';
    static props = { ...standardWidgetProps };

    setup() {
        this.dialogService = useService('dialog');
    }

    async _openPermissionPanel (event) {
        this.dialogService.add(DocumentsPermissionPanel, {
            document: {id: this.props.record.data.documents_employee_folder_id.id},
        });
    }
}


export const hrDocumentSettingPermissionPanel = {
    component: SettingDocumentPermissionWidget,
};

registry.category('view_widgets').add('hr_document_setting_permission_widget', hrDocumentSettingPermissionPanel);

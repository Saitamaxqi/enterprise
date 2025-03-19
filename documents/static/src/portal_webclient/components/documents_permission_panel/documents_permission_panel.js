import { DocumentsPermissionPanel } from "@documents/components/documents_permission_panel/documents_permission_panel";
import { patch } from "@web/core/utils/patch";

patch(DocumentsPermissionPanel.prototype, {
    get membersAccessExtended() {
        return false;
    },
    get anyMembersWithoutAccess() {
        return false;
    },
    get partnersRoleIsDirty() {
        return null;
    },
    get partnersAccessExpDateIsDirty() {
        return null;
    },
});

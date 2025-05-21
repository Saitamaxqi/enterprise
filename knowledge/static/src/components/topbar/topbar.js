import { KnowledgeFormStatusIndicator } from "@knowledge/components/form_status_indicator/form_status_indicator";
import KnowledgeHierarchy from "@knowledge/components/hierarchy/hierarchy";
import { OptionsDropdown } from "@knowledge/components/options_dropdown/options_dropdown";
import { PermissionPanel } from "@knowledge/components/permission_panel/permission_panel";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component, onWillStart, reactive, useState } from "@odoo/owl";

class KnowledgeTopbar extends Component {
    static template = "knowledge.KnowledgeTopbar";
    static props = standardWidgetProps;
    static components = {
        KnowledgeHierarchy,
        KnowledgeFormStatusIndicator,
        OptionsDropdown,
    };

    setup() {
        super.setup();

        this.permissionPopover = usePopover(PermissionPanel, {
            closeOnClickAway: true,
            env: this.env,
            arrow: false,
            onClose: () => (this.state.shareBtnIsActive = false),
            position: "bottom-end",
        });
        this.state = useState({
            shareBtnIsActive: false,
        });
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());
        this.chatterPanelState = useState(this.env.chatterPanelState);
        this.propertiesPanelState = useState(this.env.propertiesPanelState);

        onWillStart(async () => {
            this.isInternalUser = await user.hasGroup("base.group_user");
        });

        this.reactiveRecordWrapper = reactive({ record: this.props.record });
        useRecordObserver((record) => {
            this.reactiveRecordWrapper.record = record;
        });
    }

    get chatterButtonTitle() {
        return this.chatterPanelState.isDisplayed
            ? _t("Close chatter panel")
            : _t("Open chatter panel");
    }

    get commentButtonTitle() {
        return this.commentsState.displayMode === "panel"
            ? _t("Close comments panel")
            : _t("Open comments panel");
    }

    get displayCommentsPanelButton() {
        return (
            this.commentsState.displayMode === "panel" ||
            Object.keys(this.commentsState.threadRecords).length
        );
    }

    get favoriteButtonTile() {
        return this.props.record.data.is_user_favorite
            ? _t("Remove from favorites")
            : _t("Add to favorites");
    }

    toggleComments() {
        if (this.commentsState.displayMode === "handler") {
            this.commentsState.displayMode = "panel";
        } else {
            this.commentsState.displayMode = "handler";
        }
    }

    togglePermissionPanel(event) {
        if (this.permissionPopover.isOpen) {
            this.permissionPopover.close();
        } else {
            if (this.props.record.dirty) {
                this.props.record.save();
            }
            this.permissionPopover.open(event.currentTarget, {
                reactiveRecordWrapper: this.reactiveRecordWrapper,
            });
            this.state.shareBtnIsActive = true;
        }
    }
}

export const knowledgeTopbar = {
    component: KnowledgeTopbar,
    fieldDependencies: [
        { name: "create_uid", type: "many2one", relation: "res.users" },
        { name: "display_name", type: "char" },
        { name: "last_edition_uid", type: "many2one", relation: "res.users" },
        { name: "active", type: "boolean" },
        { name: "article_properties", type: "jsonb" },
        { name: "cover_image_id", type: "many2one", relation: "knowledge.cover" },
        { name: "full_width", type: "boolean" },
        { name: "icon", type: "char" },
        { name: "inherited_permission", type: "char"},
        { name: "inherited_permission_parent_id", type: "many2one", relation: "knowledge.article"},
        { name: "is_article_item", type: "boolean" },
        { name: "is_locked", type: "boolean" },
        { name: "is_desynchronized", type: "boolean"},
        { name: "is_user_favorite", type: "boolean" },
        { name: "name", type: "char" },
        { name: "parent_id", type: "char" },
        { name: "parent_path", type: "char" },
        { name: "root_article_id", type: "many2one", relation: "knowledge.article" },
        { name: "has_item_parent", type: "boolean" },
        { name: "is_listed_in_templates_gallery", type: "boolean" },
        { name: "to_delete", type: "boolean" },
        { name: "user_can_write", type: "boolean" },
    ],
};

registry.category("view_widgets").add("knowledge_topbar", knowledgeTopbar);

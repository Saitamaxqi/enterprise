import { browser } from "@web/core/browser/browser";
import { formatDateTime } from '@web/core/l10n/dates';
import { rpc } from "@web/core/network/rpc";
import { usePopover } from "@web/core/popover/popover_hook";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { _t } from "@web/core/l10n/translation";

import { getRandomIcon } from '@knowledge/js/knowledge_utils';
import KnowledgeHierarchy from '@knowledge/components/hierarchy/hierarchy';
import MoveArticleDialog from '@knowledge/components/move_article_dialog/move_article_dialog';
import { PermissionPanel } from '@knowledge/components/permission_panel/permission_panel';
import { KnowledgeFormStatusIndicator } from "@knowledge/components/form_status_indicator/form_status_indicator";
import { KNOWLEDGE_READONLY_EMBEDDINGS } from "@knowledge/editor/embedded_components/embedding_sets";
import { READONLY_MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";

import { Component, onWillStart, reactive, useEffect, useRef, useState } from "@odoo/owl";

class KnowledgeTopbar extends Component {
    static template = "knowledge.KnowledgeTopbar";
    static props = {
        ...standardWidgetProps,
    };
    static components = {
        KnowledgeHierarchy,
        KnowledgeFormStatusIndicator,
    };

    setup() {
        super.setup();
        this.actionService = useService('action');
        this.dialog = useService('dialog');
        this.notification = useService('notification');
        this.orm = useService('orm');
        this.uiService = useService("ui");

        this.permissionPopover = usePopover(PermissionPanel, {
            closeOnClickAway: true,
            env: this.env,
            arrow: false,
            onClose: () => (this.state.shareBtnIsActive = false),
            position: "bottom-end",
        });

        this.optionsBtn = useRef('optionsBtn');

        this.formatDateTime = formatDateTime;

        this.state = useState({
            addingProperty: false,
            displayChatter: false,
            displayPropertyPanel: !this.articlePropertiesIsEmpty,
            shareBtnIsActive: false,
        });
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());

        this.openChat = useOpenChat('res.users');

        onWillStart(async () => {
            this.isInternalUser = await user.hasGroup('base.group_user');
        });

        useEffect((optionsBtn) => {
            // Refresh "last edited" and "create date" when opening the options
            // panel
            if (optionsBtn) {
                optionsBtn.addEventListener(
                    'shown.bs.dropdown',
                    () => this._setDates()
                );
            }
        }, () => [this.optionsBtn.el]);

        this.reactiveRecordWrapper = reactive({ record: this.props.record });
        useRecordObserver((record) => {
            this.reactiveRecordWrapper.record = record;
        });
    }

    get chatterButtonTitle() {
        return this.state.displayChatter ? _t("Close chatter panel") : _t("Open chatter panel");
    }

    get commentButtonTitle() {
        return this.commentsState.displayMode === "panel" ? _t("Close comments panel") : _t("Open comments panel");
    }

    get displayCommentsPanelButton() {
        return (
            this.commentsState.displayMode === "panel" ||
            Object.keys(this.commentsState.threadRecords).length
        );
    }

    /**
     * Adds a random cover using unsplash. If unsplash throws an error (service
     * down/keys unset), opens the cover selector instead.
     * @param {Event} event
     */
    async addCover(event) {
        // Disable button to prevent multiple calls
        event.target.classList.add('disabled');
        this.env.ensureArticleName();
        let res = {};
        try {
            res = await rpc(`/knowledge/article/${this.props.record.resId}/add_random_cover`, {
                query: this.props.record.data.name,
                orientation: 'landscape',
            });
        } catch (e) {
            console.error(e);
        }
        if (res.cover_id) {
            await this.props.record.update({cover_image_id: [res.cover_id]});
        } else {
            // Unsplash keys unset or rate limit exceeded
            this.env.openCoverSelector();
        }
        event.target.classList.remove('disabled');
    }

    /**
     * Add a random icon to the article.
     * @param {Event} event
     */
    async addIcon(event) {
        this.props.record.update({icon: await getRandomIcon()});
    }

    _setDates() {
        if (this.props.record.data.create_date && this.props.record.data.last_edition_date) {
            this.state.createDate = this.props.record.data.create_date.toRelative();
            this.state.editionDate = this.props.record.data.last_edition_date.toRelative();
        }
    }

    get articlePropertiesIsEmpty() {
        return this.props.record.data.article_properties.filter((prop) => !prop.definition_deleted).length === 0;
    }

    toggleProperties() {
        this.state.displayPropertyPanel = !this.state.displayPropertyPanel;
        this.env.bus.trigger('KNOWLEDGE:TOGGLE_PROPERTIES', {displayPropertyPanel: this.state.displayPropertyPanel});
        if (this.state.addingProperty) {
            this.state.addingProperty = false;
        }
    }

    addProperties() {
        this.state.displayPropertyPanel = true;
        this.state.addingProperty = true;
        this.env.bus.trigger('KNOWLEDGE:TOGGLE_PROPERTIES', {displayPropertyPanel: true});
    }

    toggleComments() {
        if (this.commentsState.displayMode === "handler") {
            this.commentsState.displayMode = "panel";
        } else {
            this.commentsState.displayMode = "handler";
        }
    }

    toggleFullWidth() {
        this.props.record.update({full_width: !this.props.record.data.full_width});
        browser.dispatchEvent(new Event("resize"));
    }

    /**
     * Copy the current article in private section and open it.
     */
    async cloneArticle() {
        await this.env._saveIfDirty();
        const articleIds = await this.orm.call(
            'knowledge.article',
            'action_make_copy',
            [this.props.record.resId]
        );
        this.env.openArticle(articleIds[0], true);
    }

    /**
     * Use the browser print as wkhtmltopdf sadly does not handle emojis / embed views / ...
     * (Investigation shows that it would be complicated to add that support).
     *
     * We load the printing assets of knowledge before asking the window to "print".
     * These assets are loaded dynamically and not included in the base backend assets because they
     * alter some generic parts of the layout, which other apps may not want.
     *
     * (Note that those assets are never "unloaded", meaning it requires a reload of the webclient
     * to remove them, which is considered acceptable as very niche).
     *
     */
    async exportToPdf() {
        window.print();
    }

    async setLockStatus(newLockStatus) {
        await this.props.record.model.root.isDirty();
        await this.env._saveIfDirty();
        await this.orm.call(
            'knowledge.article',
            `action_set_${newLockStatus ? 'lock' : 'unlock'}`,
            [this.props.record.resId],
        );
        await this.props.record.load();
    }

    /**
     * Show the Dialog allowing to move the current article.
     */
    async onMoveArticleClick() {
        await this.env._saveIfDirty();
        this.dialog.add(MoveArticleDialog, {knowledgeArticleRecord: this.props.record});
    }

    /**
     * Show/hide the chatter. When showing it, it fetches data required for
     * new messages, activities, ...
     */
    toggleChatter() {
        if (this.props.record.resId) {
            this.state.displayChatter = !this.state.displayChatter;
            this.env.bus.trigger('KNOWLEDGE:TOGGLE_CHATTER', {displayChatter: this.state.displayChatter});
        }
    }
    /**
     * Open the history dialog.
     */
    async openHistory() {
        if (this.props.record.resId) {
            await this.env.model.root.save();

            const versionedFieldName = 'body';
            const historyMetadata = this.props.record.data["html_field_history_metadata"]?.[versionedFieldName];
            if (historyMetadata) {
                this.dialog.add(
                    HistoryDialog,
                    {
                        recordId: this.props.record.resId,
                        recordModel: this.props.record.resModel,
                        versionedFieldName: versionedFieldName,
                        historyMetadata: historyMetadata,
                        restoreRequested: (html, close) => {
                            const restoredData = {};
                            restoredData[versionedFieldName] = html;
                            this.props.record.update(restoredData);
                            close();
                        },
                        embeddedComponents: [
                            ...READONLY_MAIN_EMBEDDINGS,
                            ...KNOWLEDGE_READONLY_EMBEDDINGS,
                        ],
                    }
                );
            }
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

    async unarchiveArticle() {
        await this.orm.call('knowledge.article', 'action_unarchive', [this.props.record.resId]);
        await this.props.record.load();
    }

    /**
     * Set the value of is_article_item for the current record.
     * @param {boolean} newArticleItemStatus: new is_article_item value
     */
    async setIsArticleItem(newArticleItemStatus) {
        await this.props.record.update({is_article_item: newArticleItemStatus});
    }

    async sendToTrash() {
        await this.orm.call('knowledge.article', 'action_send_to_trash', [this.props.record.resId]);
        await this.actionService.doAction(
            await this.orm.call('knowledge.article', 'action_redirect_to_parent', [this.props.record.resId]),
            {stackPosition: 'replaceCurrentAction'}
        );
    }

    async listArticleInTemplateGallery() {
        await this.env._saveIfDirty();
        await this.orm.write("knowledge.article", [this.props.record.resId], {
            is_listed_in_templates_gallery: true,
        });
        await this.props.record.load();
        this.notification.add(_t("Article added to the list of Templates"), {
            type: "success",
        });
    }

    async unlistArticleFromTemplateGallery() {
        await this.env._saveIfDirty();
        await this.orm.write("knowledge.article", [this.props.record.resId], {
            is_listed_in_templates_gallery: false,
        });
        await this.props.record.load();
        this.notification.add(_t("Article removed from the list of Templates"), {
            type: "success",
        });
    }

    /**
     * @param {Event} event
     * @param {Proxy} member
     */
    async _onMemberAvatarClick(event, userId) {
        event.preventDefault();
        event.stopPropagation();
        if (userId) {
            await this.openChat(userId);
        }
    }
}

export const knowledgeTopbar = {
    component: KnowledgeTopbar,
    fieldDependencies: [
        { name: "create_uid", type: "many2one", relation: "res.users" },
        { name: "html_field_history_metadata", type: "jsonb" },
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
        { name: "is_listed_in_templates_gallery", type: "boolean" },
    ],
};

registry.category('view_widgets').add('knowledge_topbar', knowledgeTopbar);

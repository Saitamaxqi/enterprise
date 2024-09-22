import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { KNOWLEDGE_PLUGINS } from "@knowledge/editor/plugin_sets";
import { registry } from "@web/core/registry";
import { useState, useSubEnv } from "@odoo/owl";
import { KnowledgeHtmlViewer } from "../knowledge_html_viewer/knowledge_html_viewer";
import { CallbackRecorder } from "@web/search/action_hook";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { useService } from "@web/core/utils/hooks";

export class KnowledgeHtmlField extends HtmlField {
    static components = {
        ...HtmlField.components,
        HtmlViewer: KnowledgeHtmlViewer,
    };
    setup() {
        super.setup();
        useSubEnv({
            __onLayoutGeometryChange__: new CallbackRecorder(),
        });
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());
        useRecordObserver((record) => {
            if (record.resId !== this.commentsState.articleId) {
                this.commentsService.setArticleId(record.resId);
                this.commentsService.loadRecords(record.resId, {
                    ignoreBatch: true,
                    includeLoaded: true,
                });
            }
        });
    }

    getConfig() {
        const config = super.getConfig();
        config.Plugins.push(...KNOWLEDGE_PLUGINS);
        config.onLayoutGeometryChange = () => this.onLayoutGeometryChange();
        return config;
    }

    getReadonlyConfig() {
        const config = super.getReadonlyConfig();
        config.onLayoutGeometryChange = () => this.onLayoutGeometryChange();
        return config;
    }

    onLayoutGeometryChange() {
        for (const cb of this.env.__onLayoutGeometryChange__.callbacks) {
            cb();
        }
    }
}

export const knowledgeHtmlField = {
    ...htmlField,
    component: KnowledgeHtmlField,
};

registry.category("fields").add("knowledge_html", knowledgeHtmlField);

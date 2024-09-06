import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { AutofocusPlugin } from "@knowledge/editor/plugins/autofocus_plugin/autofocus_plugin";
import { KnowledgeArticlePlugin } from "@knowledge/editor/plugins/article_plugin/article_plugin";
import { KnowledgeCommentsPlugin } from "@knowledge/editor/plugins/comments_plugin/comments_plugin";
import { ArticleIndexPlugin } from "@knowledge/editor/embedded_components/plugins/article_index_plugin/article_index_plugin";
import { EmbeddedClipboardPlugin } from "@knowledge/editor/embedded_components/plugins/embedded_clipboard_plugin/embedded_clipboard_plugin";
import { EmbeddedViewPlugin } from "@knowledge/editor/embedded_components/plugins/embedded_view_plugin/embedded_view_plugin";

MAIN_PLUGINS.push(KnowledgeArticlePlugin);

export const KNOWLEDGE_PLUGINS = [AutofocusPlugin, KnowledgeCommentsPlugin];

export const KNOWLEDGE_EMBEDDED_COMPONENT_PLUGINS = [
    ArticleIndexPlugin,
    EmbeddedClipboardPlugin,
    EmbeddedViewPlugin,
];

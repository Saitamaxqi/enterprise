import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { AutofocusPlugin } from "@knowledge/editor/plugins/autofocus_plugin/autofocus_plugin";
import { KnowledgeArticlePlugin } from "@knowledge/editor/plugins/article_plugin/article_plugin";
import { KnowledgeCommentsPlugin } from "@knowledge/editor/plugins/comments_plugin/comments_plugin";

MAIN_PLUGINS.push(KnowledgeArticlePlugin);

export const KNOWLEDGE_PLUGINS = [AutofocusPlugin, KnowledgeCommentsPlugin];

export const KNOWLEDGE_EMBEDDED_COMPONENT_PLUGINS = [];

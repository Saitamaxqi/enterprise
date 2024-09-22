import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { KnowledgeArticlePlugin } from "@knowledge/editor/plugins/article_plugin/article_plugin";
import { KnowledgeCommentsPlugin } from "@knowledge/editor/plugins/comments_plugin/comments_plugin";

MAIN_PLUGINS.push(KnowledgeArticlePlugin);

export const KNOWLEDGE_PLUGINS = [KnowledgeCommentsPlugin];

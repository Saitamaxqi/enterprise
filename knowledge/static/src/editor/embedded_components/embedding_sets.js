import { macrosClipboardEmbedding } from "@knowledge/editor/embedded_components/backend/clipboard/macros_embedded_clipboard";
import { macrosFileEmbedding } from "@knowledge/editor/embedded_components/backend/file/macros_file";
import { readonlyMacrosFileEmbedding } from "@knowledge/editor/embedded_components/backend/file/readonly_macros_file";
import { articleIndexEmbedding } from "@knowledge/editor/embedded_components/backend/article_index/article_index";
import { readonlyArticleIndexEmbedding } from "@knowledge/editor/embedded_components/core/article_index/readonly_article_index";

export const KNOWLEDGE_EMBEDDINGS = [
    articleIndexEmbedding,
    macrosClipboardEmbedding,
    macrosFileEmbedding,
];

export const KNOWLEDGE_READONLY_EMBEDDINGS = [
    macrosClipboardEmbedding,
    readonlyArticleIndexEmbedding,
    readonlyMacrosFileEmbedding,
];

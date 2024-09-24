import { articleIndexEmbedding } from "@knowledge/editor/embedded_components/backend/article_index/article_index";
import { readonlyArticleIndexEmbedding } from "@knowledge/editor/embedded_components/core/article_index/readonly_article_index";

export const KNOWLEDGE_EMBEDDINGS = [
    articleIndexEmbedding,
];

export const KNOWLEDGE_READONLY_EMBEDDINGS = [
    readonlyArticleIndexEmbedding,
];

import { accountReportEmbedding } from "@accountant_knowledge/editor/embedded_components/backend/account_report/account_report";
import { readonlyAccountReportEmbedding } from "@accountant_knowledge/editor/embedded_components/core/account_report/account_report";
import {
    KNOWLEDGE_EMBEDDINGS,
    KNOWLEDGE_READONLY_EMBEDDINGS,
} from "@knowledge/editor/embedded_components/embedding_sets";

KNOWLEDGE_EMBEDDINGS.push(...[accountReportEmbedding]);

KNOWLEDGE_READONLY_EMBEDDINGS.push(...[readonlyAccountReportEmbedding]);

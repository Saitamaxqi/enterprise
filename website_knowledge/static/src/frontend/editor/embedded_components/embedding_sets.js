import { readonlyExcalidrawEmbedding } from "@html_editor/others/embedded_components/core/excalidraw/readonly_excalidraw";
import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import { readonlyTableOfContentEmbedding } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { videoEmbedding } from "@html_editor/others/embedded_components/core/video/video";

export const KNOWLEDGE_PUBLIC_EMBEDDINGS = [
    readonlyExcalidrawEmbedding,
    readonlyFileEmbedding,
    readonlyTableOfContentEmbedding,
    videoEmbedding,
];

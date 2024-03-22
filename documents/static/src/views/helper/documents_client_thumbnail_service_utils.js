import { loadPDFJSAssets } from "@web/core/utils/pdfjs";

/**
 * @return {Promise<{thumbnail: string | undefined, pdfEnabled: boolean}>}
 */
export async function getPdfThumbnail(record, width, height) {
    let initialWorkerSrc = false;
    let thumbnail = undefined;
    try {
        await loadPDFJSAssets();
        // Force usage of worker to avoid hanging the tab.
        initialWorkerSrc = globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc;
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc =
            "/web/static/lib/pdfjs/build/pdf.worker.js";
    } catch {
        return { thumbnail, pdfEnabled: false };
    }
    try {
        const pdf = await globalThis.pdfjsLib.getDocument(
            `/documents/content/${encodeURIComponent(record.data.access_token)}?download=0`
        ).promise;
        const page = await pdf.getPage(1);

        // Render first page onto a canvas
        const viewPort = page.getViewport({ scale: 1 });
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const scale = canvas.width / viewPort.width;
        await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport: page.getViewport({ scale }),
        }).promise;
        thumbnail = canvas.toDataURL("image/jpeg").replace("data:image/jpeg;base64,", "");
    } catch (_error) {
        if (
            _error.name !== "UnexpectedResponseException" &&
            _error.status &&
            _error.status !== 403
        ) {
            thumbnail = false;
        }
    } finally {
        // Restore pdfjs's state
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
    }
    return { thumbnail, pdfEnabled: true };
}

/**
 * @return {Promise<{thumbnail: string}>}
 */
export async function getWebpThumbnail(img, width, height) {
    const canvas = document.createElement("canvas");
    const widthRatio = width / img.width;
    const heightRatio = height / img.height;
    const scale = Math.min(widthRatio, heightRatio, 1);
    const scaledWidth = img.width * scale;
    const scaledHeight = img.height * scale;
    canvas.width = scaledWidth;
    canvas.height = scaledHeight;
    canvas.getContext("2d").drawImage(img, 0, 0, scaledWidth, scaledHeight);
    const thumbnail = canvas.toDataURL("image/jpeg").replace("data:image/jpeg;base64,", "");
    return { thumbnail };
}

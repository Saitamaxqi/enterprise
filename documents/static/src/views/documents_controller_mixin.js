export const DocumentsControllerMixin = (component) =>
    class extends component {
        get modelParams() {
            const modelParams = super.modelParams;
            modelParams.multiEdit = true;
            return modelParams;
        }
    };

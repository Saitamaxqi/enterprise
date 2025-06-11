import { SyncCache } from "@html_builder/utils/sync_cache";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { FormOptionPlugin } from "@website/builder/plugins/form/form_option_plugin";
import { getModelName } from "@website/builder/plugins/form/utils";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ModelCache extends SyncCache {
    async preload(params) {
        const result = await super.preload(params);
        this.syncCache.set(JSON.stringify({ modelName: result.model, modelId: undefined }), result);
        this.syncCache.set(JSON.stringify({ modelName: undefined, modelId: result.id }), result);
        this.syncCache.set(JSON.stringify({ modelName: result.model, modelId: result.id }), result);
        return result;
    }
    get(params) {
        return super.get({ modelName: params.modelName, modelId: params.modelId });
    }
}

const IR_MODEL_SPEC = {
    model: {},
    name: {},
    website_form_label: {},
    website_form_key: {},
    website_form_access: {},
};

let appliedModel;

patch(FormOptionPlugin, {
    // static
    shared: [
        ...(FormOptionPlugin.shared || []),
        "getModelsCache",
        "studioIsFormAccessEditable",
        "studioPreloadModel",
    ],
});
patch(FormOptionPlugin.prototype, {
    setup() {
        super.setup();
        this.studioModelsCache = new ModelCache(this._studioFetchModels.bind(this));
    },
    getModelsCache(formEl) {
        const models = super.getModelsCache();
        if (!models) {
            // Do not try to load if form was never initialized.
            return models;
        }
        const currentModel = appliedModel || getModelName(formEl);
        if (currentModel && !models.find((m) => m.model === currentModel)) {
            return [...models, this.studioModelsCache.get({ modelName: currentModel })];
        }
        return models;
    },
    async fetchModels(formEl) {
        const formModels = await super.fetchModels(formEl);
        const currentModel = appliedModel || getModelName(formEl);
        if (formModels.some((m) => m.model === currentModel)) {
            return formModels;
        }
        await this.studioPreloadModel({ modelName: currentModel });
        const studioModels = new Set(this.studioModelsCache.syncCache.values());
        const allModels = [...formModels, ...studioModels];
        return allModels;
    },
    async _fetchModels() {
        const models = await super._fetchModels();
        for (const model of models) {
            model.isFormAccessEditable = this.studioIsFormAccessEditable(model);
            model.website_form_access = true;
        }
        return models;
    },
    async studioPreloadModel({ modelName, modelId }) {
        return this.studioModelsCache.preload({ modelName, modelId });
    },
    async _studioFetchModels({ modelName, modelId }) {
        const domain = modelName ? [["model", "=", modelName]] : [["id", "=", modelId]];
        const res = await this.services.orm.webSearchRead("ir.model", domain, {
            specification: IR_MODEL_SPEC,
        });
        const model = res.records[0];
        if (!model.website_form_label) {
            model._isVirtual = true;
            model.website_form_label = this.studioGetNewFormLabel(model);
        }
        model.isFormAccessEditable = this.studioIsFormAccessEditable(model);
        return model;
    },
    studioGetNewFormLabel(model) {
        return _t("Create %s", model.name);
    },
    studioIsFormAccessEditable(model) {
        return (
            model &&
            (model.website_form_key === false ||
                model.website_form_key.startsWith("website_studio."))
        );
    },
});

export class StudioFormOptionPlugin extends Plugin {
    static id = "studioFormOption";
    static dependencies = ["builderActions", "builderOptions", "websiteFormOption"];
    static shared = ["setFormAccess", "saveFormAccess"];
    resources = {
        builder_actions: {
            StudioMoreModelsAction,
            StudioToggleFormAccessAction,
        },
        save_handlers: [
            async () => {
                for (const formEl of this.editable.querySelectorAll(".s_website_form")) {
                    const models = this.dependencies.websiteFormOption.getModelsCache(formEl);
                    // Untouched => models were not loaded.
                    if (models) {
                        const targetModelName = getModelName(formEl);
                        const activeForm = models.find((m) => m.model === targetModelName);
                        await this.saveFormAccess(activeForm);
                    }
                }
            }
        ],
    };
    selectModel() {
        return new Promise((resolve) => {
            this.services.dialog.add(
                SelectCreateDialog,
                {
                    title: _t("Select model"),
                    noCreate: true,
                    multiSelect: false,
                    resModel: "ir.model",
                    context: {
                        "list_view_ref": "website_studio.select_simple_ir_model",
                    },
                    domain: ["&", ["abstract", "=", false], ["transient", "=", false]],
                    onSelected: (resIds) => resolve(resIds[0]),
                },
                {
                    onClose: () => resolve(false),
                }
            );
        });
    }
    isFormAccessEditable(model) {
        return this.dependencies.websiteFormOption.studioIsFormAccessEditable(model);
    }
    async setFormAccess(model, newValue) {
        if (!model) {
            return;
        }
        if (this.isFormAccessEditable(model)) {
            const toWrite = { website_form_access: newValue };
            if (!("_old_website_form_access" in model)) {
                model._old_website_form_access = model.website_form_access;
            }
            if (newValue && model._isVirtual) {
                toWrite.website_form_label = model.website_form_label;
                toWrite.website_form_key = `website_studio.${model.model}`;
            }
            Object.assign(model, toWrite);
        }
    }
    async saveFormAccess(model) {
        if (
            model &&
            "_old_website_form_access" in model &&
            model._old_website_form_access !== model.website_form_access
        ) {
            const { website_form_access, website_form_key, website_form_label } = model;
            const toWrite = {
                website_form_access,
            };
            if (model._isVirtual) {
                Object.assign(toWrite, {
                    website_form_key,
                    website_form_label,
                });
            }
            const res = await this.services.orm.webSave("ir.model", [model.id], toWrite, {
                specification: IR_MODEL_SPEC,
            });
            Object.assign(model, res[0]);
            delete model._old_website_form_access;
        }
    }
}

class StudioMoreModelsAction extends BuilderAction {
    static id = "studioMoreModels";
    static dependencies = ["studioFormOption", "websiteFormOption", "builderActions"];
    isApplied() {
        return false;
    }
    async load(spec) {
        const modelId = await this.dependencies.studioFormOption.selectModel();
        if (!modelId) {
            return;
        }
        const model = await this.dependencies.websiteFormOption.studioPreloadModel({ modelId });
        appliedModel = model.model;
        const getAction = this.dependencies.builderActions.getAction;
        const selectLoadResult = await getAction("selectAction").load({
            ...spec, value: model.id
        });
        appliedModel = undefined;
        return { model, selectLoadResult };
    }
    async apply(spec) {
        if (!spec.loadResult?.model) {
            return;
        }
        const getAction = this.dependencies.builderActions.getAction;
        appliedModel = spec.loadResult.model.model;
        await getAction("selectAction").apply({
            ...spec,
            value: spec.loadResult.model.id,
            loadResult: spec.loadResult.selectLoadResult,
        });
        appliedModel = undefined;
        this.dependencies.studioFormOption.setFormAccess(spec.loadResult.model, true);
    }
}

class StudioToggleFormAccessAction extends BuilderAction {
    static id = "studioToggleFormAccess";
    static dependencies = ["websiteFormOption", "studioFormOption"]
    isApplied({ editingElement: formEl }) {
        const models = this.dependencies.websiteFormOption.getModelsCache(formEl);
        const targetModelName = getModelName(formEl);
        const activeForm = models.find((m) => m.model === targetModelName);
        return activeForm?.website_form_access;
    }
    async apply({ editingElement: formEl, value }) {
        const models = this.dependencies.websiteFormOption.getModelsCache(formEl);
        const targetModelName = getModelName(formEl);
        const activeForm = models.find((m) => m.model === targetModelName);
        this.dependencies.studioFormOption.setFormAccess(activeForm, true);
        await this.dependencies.studioFormOption.saveFormAccess(activeForm);
    }
    async clean({ editingElement: formEl }) {
        const models = this.dependencies.websiteFormOption.getModelsCache(formEl);
        const targetModelName = getModelName(formEl);
        const activeForm = models.find((m) => m.model === targetModelName);
        this.dependencies.studioFormOption.setFormAccess(activeForm, false);
        await this.dependencies.studioFormOption.saveFormAccess(activeForm);
    }
}

registry.category("website-plugins").add(StudioFormOptionPlugin.id, StudioFormOptionPlugin);

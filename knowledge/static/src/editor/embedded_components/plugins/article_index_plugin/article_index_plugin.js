import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

export class ArticleIndexPlugin extends Plugin {
    static name = "articleIndex";
    static dependencies = ["embedded_components", "dom", "selection"];
    static resources = (p) => ({
        powerboxCategory: [
            {
                id: "knowledge",
                name: _t("Knowledge"),
                sequence: 20,
            },
        ],
        powerboxItems: [
            {
                category: "knowledge",
                name: _t("Index"),
                description: _t("Show nested articles"),
                fontawesome: "fa-list",
                action: () => {
                    p.insertArticleIndex();
                },
            },
        ],
    });

    insertArticleIndex() {
        const articleIndexBlueprint = renderToElement("knowledge.ArticleIndexBlueprint");
        this.shared.domInsert(articleIndexBlueprint);
        this.dispatch("ADD_STEP");
    }
}

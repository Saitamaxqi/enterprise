// HOOT FIXME: remove this once document is converted to Hoot and we can import their helper
export function getEnrichedSearchArch(searchArch = "<search></search>") {
    var searchPanelArch = `
        <searchpanel class="o_documents_search_panel">
            <field name="folder_id" string="Folders"/>
        </searchpanel>
    `;
    return searchArch.split("</search>")[0] + searchPanelArch + "</search>";
}

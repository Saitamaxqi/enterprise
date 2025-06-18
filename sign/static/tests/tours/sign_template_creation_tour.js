import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { queryFirst } from "@odoo/hoot-dom";
import { _t } from "@web/core/l10n/translation";

function triggerDragEvent(element, type, data = {}) {
    const event = new DragEvent(type, { bubbles: true });
    for (const key in data) {
        Object.defineProperty(event, key, {
            value: data[key],
        });
    }
    element.dispatchEvent(event);
}

export function dragAndDropSignItemAtHeight(from, height = 0.5, width = 0.5) {
    const iframe = document.querySelector("iframe");
    const to = queryFirst(`:iframe .page[data-page-number="1"]`);
    const toPosition = to.getBoundingClientRect();
    toPosition.x += iframe.contentWindow.scrollX + to.clientWidth * width;
    toPosition.y += iframe.contentWindow.scrollY + to.clientHeight * height;

    const dataTransferObject = {};
    const dataTransferMock = {
        setData: (key, value) => {
            dataTransferObject[key] = value;
        },
        getData: (key) => dataTransferObject[key],
        setDragImage: () => {},
        items: [],
    };

    triggerDragEvent(from, "dragstart", {
        dataTransfer: dataTransferMock,
    });

    triggerDragEvent(to, "drop", {
        pageX: toPosition.x,
        pageY: toPosition.y,
        dataTransfer: dataTransferMock,
    });

    triggerDragEvent(from, "dragend");
}

export function createSelectionRectangle(startPos=0.25, endPos=0.75) {
    const viewerContainer = queryFirst(`:iframe #viewerContainer`);
    const page = queryFirst(`:iframe .page[data-page-number="1"]`);
    const pageRect = page.getBoundingClientRect();

    const startX = pageRect.width * startPos;
    const startY = pageRect.height * startPos;
    const endX = pageRect.width * endPos;
    const endY = pageRect.height * endPos;
    const mousemoveEvent = new MouseEvent('mousemove', {
        bubbles: true,
        clientX: startX,
        clientY: startY
    });
    viewerContainer.dispatchEvent(mousemoveEvent);

    const mousedownEvent = new MouseEvent('mousedown', {
        bubbles: true,
        clientX: startX,
        clientY: startY,
        button: 0
    });
    viewerContainer.dispatchEvent(mousedownEvent);

    const mousemoveEvent2 = new MouseEvent('mousemove', {
        bubbles: true,
        clientX: endX,
        clientY: endY
    });
    viewerContainer.dispatchEvent(mousemoveEvent2);

    const mouseupEvent = new MouseEvent('mouseup', {
        bubbles: true,
        clientX: endX,
        clientY: endY
    });
    viewerContainer.dispatchEvent(mouseupEvent);
}

registry.category("web_tour.tours").add("sign_template_creation_tour", {
    url: "/odoo?debug=1",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Sign App",
            trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
            run: "click",
        },
        {
            content: "Click on Template Menu",
            trigger: 'a[data-menu-xmlid="sign.sign_template_menu"]',
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_last_breadcrumb_item > span:contains('Templates')",
        },
        {
            content: "Remove My Favorites filter",
            trigger: ".o_cp_searchview .o_facet_remove",
            run: "click",
        },
        {
            content: 'Search template "blank_template"',
            trigger: ".o_cp_searchview input",
            run: "fill blank_template",
        },
        {
            content: "Search Document Name",
            trigger: ".o_searchview_autocomplete .o-dropdown-item:first",
            run: "click",
        },
        {
            content: "Enter Template Edit Mode",
            trigger: '.o_kanban_record span:contains("blank_template")',
            run: "click",
        },
        {
            content: "Wait for iframe to load PDF",
            trigger: ":iframe #viewerContainer",
        },
        {
            content: "Wait for page to be loaded",
            trigger: ":iframe .page[data-page-number='1'] .textLayer",
            timeout: 30000, //In view mode, pdf loading can take a long time
        },
        {
            content: "Drop Signature Item",
            trigger: ".o_sign_field_type_button:contains(" + _t("Signature") +")",
            run() {
                dragAndDropSignItemAtHeight(this.anchor, 0.5, 0.25);
            },
        },
        {
            content: "Drop Name Sign Item",
            trigger: ".o_sign_field_type_button:contains(" + _t("Name") +")",
            run() {
                dragAndDropSignItemAtHeight(this.anchor, 0.25, 0.25);
            },
        },
        {
            content: "Drop Text Sign Item",
            trigger: ".o_sign_field_type_button:contains(" + _t("Text") +")",
            run() {
                dragAndDropSignItemAtHeight(this.anchor, 0.15, 0.25);
            },
        },
        {
            content: "Test multi-select by creating a selection rectangle",
            trigger: ":iframe .page[data-page-number='1']",
            run() {
                createSelectionRectangle(0.25, 0.75);
            }
        },
        {
            content: "Verify items are selected",
            trigger: ":iframe .o_sign_sign_item.multi_selected",
        },
        {
            content: "Test copy functionality with Ctrl+C",
            trigger: ":iframe .o_sign_sign_item.multi_selected",
            run() {
                const keyEvent = new KeyboardEvent('keydown', {
                    key: 'c',
                    code: 'KeyC',
                    ctrlKey: true,
                    bubbles: true
                });
                document.querySelector("iframe").contentDocument.dispatchEvent(keyEvent);
            }
        },
        {
            content: "Click elsewhere to prepare for paste",
            trigger: ":iframe .page[data-page-number='1']",
            run(actions) {
                const page = queryFirst(`:iframe .page[data-page-number="1"]`);
                const pageRect = page.getBoundingClientRect();
                actions.click({
                    x: pageRect.left + pageRect.width * 0.8,
                    y: pageRect.top + pageRect.height * 0.8
                });
            }
        },
        {
            content: "Test paste functionality with Ctrl+V",
            trigger: ":iframe .page[data-page-number='1']",
            run() {
                const keyEvent = new KeyboardEvent('keydown', {
                    key: 'v',
                    code: 'KeyV',
                    ctrlKey: true,
                    bubbles: true
                });
                document.querySelector("iframe").contentDocument.dispatchEvent(keyEvent);
            }
        },
        {
            content: "Test multi-select by creating a selection rectangle",
            trigger: ":iframe .page[data-page-number='1']",
            run() {
                createSelectionRectangle(0.25, 0.75);
            }
        },
        {
            content: "Verify items are selected",
            trigger: ":iframe .o_sign_sign_item.multi_selected",
        },
        {
            content: "Click on document name text to make it editable",
            trigger: ".o_sign_sidebar_document_name_text",
            run: "click",
        },
        {
            content: "Change document name",
            trigger: ".o_sign_document_name_input",
            run: "edit new-document-name && click body",
        },
        {
            trigger: ".breadcrumb .o_back_button",
            run: "click",
        },
    ],
});

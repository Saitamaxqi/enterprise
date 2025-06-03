import { describe, expect, test } from "@odoo/hoot";
import { click, animationFrame } from "@odoo/hoot-dom";
import { user } from "@web/core/user";
import { patchWithCleanup, getService, onRpc } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { createDocumentWebClient } from "./action_utils";

const tag = "sign.Document";

describe.current.tags("desktop");
defineMailModels();

test("simple rendering", async () => {
    patchWithCleanup(user, { userId: 1 });

    onRpc("/web/dataset/call_kw/sign.request.item/send_signature_accesses", () => {
        expect.step("send_messages");
        return true;
    });

    const getDataFromHTML = () => {
        expect.step("getDataFromHTML");
    };

    const config = {
        tag: tag,
        getDataFromHTML,
        actionContext: {
            need_to_sign: true,
        },
    };

    await createDocumentWebClient(config);
    await getService("action").doAction(9);
    await animationFrame();

    expect.verifySteps(["getDataFromHTML"]);

    expect(".o_sign_document").toHaveText("def", { message: "should display text from server" });
    expect(".o_sign_resend_access_button").toHaveCount(2);
    expect(".o_sign_resend_access_button:eq(0)").toHaveText("Resend");
    expect(".o_sign_resend_access_button:eq(1)").toHaveText("Send");
    expect(".o_sign_sign_directly").toHaveCount(1);

    // click on resend
    await click(".o_sign_resend_access_button");
    expect.verifySteps(["send_messages"]);
});

test("render shared document", async () => {
    const config = {
        tag: tag,
        actionContext: {
            need_to_sign: true,
            state: "shared",
        },
    };

    await createDocumentWebClient(config);
    await getService("action").doAction(9);
    await animationFrame();

    expect(".o_sign_document").toHaveText("def", { message: "should display text from server" });

    expect(".o_sign_resend_access_button").toHaveCount(0);
    expect(".o_sign_sign_directly").toHaveCount(1);
});

test("do not crash when leaving the action", async () => {
    const config = {
        tag: tag,
    };

    await createDocumentWebClient(config);

    onRpc("/sign/get_document/5/abc", (request) => {
        expect.step(new URL(request.url).pathname);
        return Promise.resolve({
            html: `
            <span>
                def
                <div class='o_sign_cp_pager'></div>
            </span>
            <iframe srcdoc="" class="o_iframe o_sign_pdf_iframe"/>`,
            context: {},
        });
    });

    await getService("action").doAction(9);
    await getService("action").doAction(9);

    expect.verifySteps(["/sign/get_document/5/abc", "/sign/get_document/5/abc"]);
});

test("show completed documents download dropdown when state is signed", async () => {
    const config = {
        tag: tag,
        actionContext: { state: "signed" },
    };

    await createDocumentWebClient(config);

    await getService("action").doAction(9);

    expect(".o_sign_download_documents_dropdown").toHaveCount(1);

    expect(".o_sign_download_single_document_dropdown_item").toHaveAttribute(
        "href",
        "/sign/download/5/abc/completed/1",
        {
            message: "should have correct download URL for a single document",
        }
    );

    expect(".o_sign_download_certificate_dropdown_item").toHaveAttribute("href", "/sign/download/5/abc/log", {
        message: "should have correct download URL for a certificate",
    });
});

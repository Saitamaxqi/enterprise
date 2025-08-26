import { expect, test } from "@odoo/hoot";
import {
    clearRegistry,
    contains,
    defineModels,
    fields,
    mountWithCleanup,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { mockMatchMedia } from "@odoo/hoot-mock";
import { animationFrame } from "@odoo/hoot-dom";
import { _makeUser, user } from "@web/core/user";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { BurgerUserMenu } from "@web/webclient/burger_menu/burger_user_menu/burger_user_menu";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";
import { browser } from "@web/core/browser/browser";

class ResUsersSettings extends webModels.ResUsersSettings {
    color_scheme = fields.Selection({
        selection: [
            ["system", "System"],
            ["light", "Light"],
            ["dark", "Dark"],
        ],
        default: "system",
    });

    _records = [
        {
            id: 1,
            color_scheme: "system",
        },
    ];
}

defineModels([ResUsersSettings]);

test.tags("desktop");
test("use 'system' color scheme (light) on desktop", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "light" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "system" } }));
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button").toHaveCount(3);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("System");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);
});

test.tags("mobile");
test("use 'system' color scheme (light) on mobile", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "light" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "system" } }));
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a").toHaveCount(1);
    expect(".o_user_menu_mobile > a button").toHaveCount(3);
    expect(".o_user_menu_mobile > a button.active").toHaveCount(1);
    expect(".o_user_menu_mobile > a button.active").toHaveText("System");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);
});

test.tags("desktop");
test("use 'system' color scheme (dark) on desktop", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "dark" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "system" } }));
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button").toHaveCount(3);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("System");
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);
});

test.tags("mobile");
test("use 'system' color scheme (dark) on mobile", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "dark" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "system" } }));
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a").toHaveCount(1);
    expect(".o_user_menu_mobile > a button").toHaveCount(3);
    expect(".o_user_menu_mobile > a button.active").toHaveCount(1);
    expect(".o_user_menu_mobile > a button.active").toHaveText("System");
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);
});

test.tags("desktop");
test("use 'light' color scheme on desktop", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "dark" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "light" } }));
    ResUsersSettings._records[0].color_scheme = "light";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button").toHaveCount(3);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);
});

test.tags("mobile");
test("use 'light' color scheme on mobile", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "dark" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "light" } }));
    ResUsersSettings._records[0].color_scheme = "light";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a").toHaveCount(1);
    expect(".o_user_menu_mobile > a button").toHaveCount(3);
    expect(".o_user_menu_mobile > a button.active").toHaveCount(1);
    expect(".o_user_menu_mobile > a button.active").toHaveText("Light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);
});

test.tags("desktop");
test("use 'dark' color scheme on desktop", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "light" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "dark" } }));
    ResUsersSettings._records[0].color_scheme = "dark";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button").toHaveCount(3);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Dark");
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);
});

test.tags("mobile");
test("use 'dark' color scheme on mobile", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "light" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "dark" } }));
    ResUsersSettings._records[0].color_scheme = "dark";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a").toHaveCount(1);
    expect(".o_user_menu_mobile > a button").toHaveCount(3);
    expect(".o_user_menu_mobile > a button.active").toHaveCount(1);
    expect(".o_user_menu_mobile > a button.active").toHaveText("Dark");
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);
});

test.tags("desktop");
test("switch to 'system' color scheme on desktop", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "dark" });
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "light" } }));
    ResUsersSettings._records[0].color_scheme = "light";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);

    await contains(".o-dropdown--menu .dropdown-item button:contains(System)").click();
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);

    await contains(".o_user_menu button").click();
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("System");
});

test.tags("mobile");
test("switch to 'system' color scheme on mobile", async () => {
    mockMatchMedia({ ["prefers-color-scheme"]: "dark" });
    let comp;
    patchWithCleanup(browser.location, {
        reload: () => {
            expect.step("reloadPage");
            comp?.render(true);
        },
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "light" } }));
    ResUsersSettings._records[0].color_scheme = "light";
    clearRegistry(registry.category("user_menuitems"));
    comp = await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a button.active").toHaveText("Light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);

    await contains(".o_user_menu_mobile > a button:contains(System)").click();
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);
    await animationFrame();
    expect(".o_user_menu_mobile > a button.active").toHaveText("System");
});

test.tags("desktop");
test("switch to 'light' color scheme on desktop", async () => {
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "dark" } }));
    ResUsersSettings._records[0].color_scheme = "dark";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Dark");
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);

    await contains(".o-dropdown--menu .dropdown-item button:contains(Light)").click();
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps(["reloadPage"]);

    await contains(".o_user_menu button").click();
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Light");
});

test.tags("mobile");
test("switch to 'light' color scheme on mobile", async () => {
    let comp;
    patchWithCleanup(browser.location, {
        reload: () => {
            expect.step("reloadPage");
            comp?.render(true);
        },
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "dark" } }));
    ResUsersSettings._records[0].color_scheme = "dark";
    clearRegistry(registry.category("user_menuitems"));
    comp = await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a button.active").toHaveText("Dark");
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);

    await contains(".o_user_menu_mobile > a button:contains(Light)").click();
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps(["reloadPage"]);
    await animationFrame();
    expect(".o_user_menu_mobile > a button.active").toHaveText("Light");
});

test.tags("desktop");
test("switch to 'dark' color scheme on desktop", async () => {
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reloadPage"),
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "light" } }));
    ResUsersSettings._records[0].color_scheme = "light";
    clearRegistry(registry.category("user_menuitems"));
    await mountWithCleanup(UserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start
    await contains(".o_user_menu button").click();

    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);

    await contains(".o-dropdown--menu .dropdown-item button:contains(Dark)").click();
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);

    await contains(".o_user_menu button").click();
    expect(".o-dropdown--menu .dropdown-item button.active").toHaveText("Dark");
});

test.tags("mobile");
test("switch to 'dark' color scheme on mobile", async () => {
    let comp;
    patchWithCleanup(browser.location, {
        reload: () => {
            expect.step("reloadPage");
            comp?.render(true);
        },
    });
    patchWithCleanup(user, _makeUser({ user_settings: { id: 1, color_scheme: "light" } }));
    ResUsersSettings._records[0].color_scheme = "light";
    clearRegistry(registry.category("user_menuitems"));
    comp = await mountWithCleanup(BurgerUserMenu);
    // The color_scheme service adds a "Theme" item to the user menu items on start

    expect(".o_user_menu_mobile > a button.active").toHaveText("Light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps([]);

    await contains(".o_user_menu_mobile > a button:contains(Dark)").click();
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reloadPage"]);
    await animationFrame();
    expect(".o_user_menu_mobile > a button.active").toHaveText("Dark");
});

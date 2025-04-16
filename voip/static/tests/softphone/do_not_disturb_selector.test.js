import { describe, test } from "@odoo/hoot";
import { advanceTime, mockDate } from "@odoo/hoot-mock";

import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Do not disturb selector show all options", async () => {
    await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-DndSelector-badge[title='Available']");
    await click("p", { text: "Do Not Disturb" });
    await contains("button", { text: "For 15 minutes" });
    await contains("button", { text: "For 1 hour" });
    await contains("button", { text: "For 3 hours" });
    await contains("button", { text: "For 8 hours" });
    await contains("button", { text: "For 24 hours" });
    await contains("button", { text: "Until I turn it back on" });
});

test("Do not disturb selector change state correctly with limited time", async () => {
    mockDate("2025-01-01 01:00:00", +0);
    await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-DndSelector-badge[title='Available']");
    await click("p", { text: "Do Not Disturb" });
    await click("button", { text: "For 15 minutes" });
    await click(".o-voip-DndSelector-badge i.text-danger");
    await contains("p", { text: "Until Jan 1, 2025, 1:15 AM" });
    advanceTime(14 * 60 * 1000);
    await contains(".o-voip-DndSelector-badge i.text-danger");
    advanceTime(1 * 60 * 1000);
    await contains(".o-voip-DndSelector-badge i.text-success");
});

test("Do not disturb selector change state correctly with infinite time", async () => {
    await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-DndSelector-badge[title='Available']");
    await click("p", { text: "Do Not Disturb" });
    await click("button", { text: "Until I turn it back on" });
    await click(".o-voip-DndSelector-badge i.text-danger");
    await contains("p", { text: "Until I turn it back on" });
    advanceTime(24 * 60 * 60 * 1000);
    await click(".o-voip-DndSelector-badge i.text-danger");
    await click(".o-dropdown-item i.text-success");
    await contains(".o-voip-DndSelector-badge i.text-success");
});

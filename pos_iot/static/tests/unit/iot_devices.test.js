import { test, expect, getFixture } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { htmlToCanvas } from "@point_of_sale/app/services/render_service";

definePosModels();

test("pos_iot_common", async () => {
    const store = await setupPosEnv();
    const hardwareProxy = store.hardwareProxy;
    const iotBoxes = hardwareProxy.iotBoxes;
    expect(store.config.useProxy).toBe(false);
    store.config.update({
        iot_device_ids: [2, 3, 4, 5],
        iface_print_via_proxy: true,
        iface_printer_id: 2,
        iface_display_id: 3,
        iface_scale_id: 5,
    });

    // IOT box loaded correctly
    expect(iotBoxes.length).toBe(1);
    expect(iotBoxes[0].name).toBe("DEMO IOT BOX");
    expect(iotBoxes[0].ip).toBe("1.1.1.1");
    expect(store.config.useProxy).toBe(true);

    // Connect the IOT box
    expect(hardwareProxy.iotBoxes[0].connected).toBeEmpty();
    await hardwareProxy.setProxyConnectionStatus("1.1.1.1", true);
    expect(hardwareProxy.connectionInfo.status).toBe("connected");
    expect(hardwareProxy.iotBoxes[0].connected).toBe(true);

    // Drivers are set properly
    expect(Object.keys(hardwareProxy.deviceControllers)).toEqual([
        "printer",
        "display",
        "scanners",
        "scale",
    ]);

    expect(store.getDisplayDeviceIP()).toBe("1.1.1.1");
    expect(store.scale._scaleDevice).not.toBeEmpty();

    // printer
    expect(store.unwatched.printers.length).toBe(1); // createPrinter() works properly
    expect(hardwareProxy.printer).toBeEmpty(); // printer isn't connected
    store.connectToProxy();
    expect(hardwareProxy.printer).not.toBeEmpty(); // printer should be connected
    const hardwareProxyPrinter = hardwareProxy.printer.device;
    expect(hardwareProxyPrinter.id).toInclude("listener");
    expect(hardwareProxyPrinter.identifier).toBe("printer_identifier");

    // print a job
    const target = getFixture();
    const node = document.createElement("div");
    node.classList.add("render-container");
    target.appendChild(node);

    const canvas = await htmlToCanvas(node, {});
    const printJobAction = await hardwareProxy.printer.sendPrintingJob(canvas);
    expect(printJobAction.result).toBe(true);

    // Open cashbox
    const openCashBoxAction = await hardwareProxy.printer.openCashbox();
    expect(openCashBoxAction.result).toBe(true);

    // disconnect the iot
    await hardwareProxy.setProxyConnectionStatus("1.1.1.1", false);
    expect(hardwareProxy.iotBoxes[0].connected).toBe(false);
    expect(hardwareProxy.connectionInfo.status).toBe("disconnected");
    expect(hardwareProxy.connectionInfo.message).toBe("DEMO IOT BOX disconnected");
});

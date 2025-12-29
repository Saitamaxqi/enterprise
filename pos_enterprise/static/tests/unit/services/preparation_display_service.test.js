import { describe, test, expect } from "@odoo/hoot";
import { definePosPrepDisplayModels } from "@pos_enterprise/../tests/unit/data/generate_model_definitions";
import {
    setupPosPrepDisplayEnv,
    createPrepDisplayTicket,
} from "@pos_enterprise/../tests/unit/utils";

definePosPrepDisplayModels();

test("toggleTime", async () => {
    const store = await setupPosPrepDisplayEnv();
    await createPrepDisplayTicket(store);
    store.toggleTime("tomorrow");
    expect(store.selectedTime).toBe("tomorrow");
});

describe("checkStateVisibility", () => {
    test("returns true for state with no filters and todo=true", async () => {
        const store = await setupPosPrepDisplayEnv();
        await createPrepDisplayTicket(store);
        const state = store.data.models["pos.prep.state"].getAll()[0];
        const visible = store.checkStateVisibility(state);
        expect(visible).toBe(true);
    });

    test("returns false for completed state in last stage", async () => {
        const store = await setupPosPrepDisplayEnv();
        await createPrepDisplayTicket(store);
        const state = store.data.models["pos.prep.state"].getAll()[0];
        state.todo = false;
        state.stage_id = store.lastStage;
        state.timeToShow = 0;
        const visible = store.checkStateVisibility(state);
        expect(visible).toBe(false);
    });
});

describe("orderNextStage", () => {
    test("returns next stage for given stage id", async () => {
        const store = await setupPosPrepDisplayEnv();
        await createPrepDisplayTicket(store);
        const stages = store.data.models["pos.prep.stage"].getAll();
        const nextStage = store.orderNextStage(stages[0].id);
        expect(nextStage.id).toBe(stages[1].id);
    });

    test("returns first stage if current is last", async () => {
        const store = await setupPosPrepDisplayEnv();
        await createPrepDisplayTicket(store);
        const lastStage = store.lastStage;
        const firstStage = store.orderNextStage(lastStage.id);
        expect(firstStage.id).toBe(store.data.models["pos.prep.stage"].getAll()[0].id);
    });
});

test("doneOrders", async () => {
    const store = await setupPosPrepDisplayEnv();
    await createPrepDisplayTicket(store);
    const states = store.data.models["pos.prep.state"].getAll();
    await store.doneOrders(states);
    expect(states.every((s) => s.todo === false)).toBe(true);
});

test("changeStateStage", async () => {
    const store = await setupPosPrepDisplayEnv();
    await createPrepDisplayTicket(store);
    const states = store.data.models["pos.prep.state"].getAll();
    await store.changeStateStage(states);
    await store.data.initData();
    expect(states[0].stage_id.id).toBe(2);
});

test("filteredOrders", async () => {
    const store = await setupPosPrepDisplayEnv();
    await createPrepDisplayTicket(store);
    const states = store.data.models["pos.prep.state"].getAll();
    expect(store.filteredOrders.length).toBe(1);
    await store.changeStateStage(states);
    await store.data.initData();
    expect(store.filteredOrders.length).toBe(0);
});

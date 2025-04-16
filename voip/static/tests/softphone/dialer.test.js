import { describe, expect, test } from "@odoo/hoot";

import { highlightMatch } from "@voip/softphone/dialer";

describe.current.tags("headless");

describe("highlightMatch", () => {
    test("base case", () => {
        const match = highlightMatch("Yuchen (yhu)", "yhu");
        expect(match.valueOf()).toBe(`Yuchen (<span class="fw-bolder">yhu</span>)`);
    });
    test("compatibility equivalence", () => {
        const match = highlightMatch("𝔖𝔥𝔯𝔢𝔨", "shrek");
        expect(match.valueOf()).toBe(`<span class="fw-bolder">𝔖𝔥𝔯𝔢𝔨</span>`);
    });
    test("with fancy diacritics", () => {
        const match = highlightMatch("Şükrü Özyıldız", "SUKRU OZYILDIZ");
        expect(match.valueOf()).toBe(`<span class="fw-bolder">Şükrü Özyıldız</span>`);
    });
    test("with different normalization forms", () => {
        const match = highlightMatch("eĥoŝanĝo ĉiuĵaŭde".normalize("NFD"), "EHOSANGO CIUJAUDE");
        expect(match.valueOf()).toBe(`<span class="fw-bolder">eĥoŝanĝo ĉiuĵaŭde</span>`);
    });
    test("with letters without canonical decomposition", () => {
        let match = highlightMatch("Bjørn Dæhlie", "ORN DAE");
        expect(match.valueOf()).toBe(`Bj<span class="fw-bolder">ørn Dæ</span>hlie`);
        match = highlightMatch("Richard Cœur de Lion", "coeur");
        expect(match.valueOf()).toBe(`Richard <span class="fw-bolder">Cœur</span> de Lion`);
    });
    test("full case folding", () => {
        let match = highlightMatch("Scleßin", "essi");
        expect(match.valueOf()).toBe(`Scl<span class="fw-bolder">eßi</span>n`);
        match = highlightMatch("Sclessin", "eßi");
        expect(match.valueOf()).toBe(`Scl<span class="fw-bolder">essi</span>n`);
        match = highlightMatch("Džemal Bijedić", "ǆ");
        expect(match.valueOf()).toBe(`<span class="fw-bolder">Dž</span>emal Bijedić`);
    });
});

import { describe, expect, test } from "@odoo/hoot";

import { normalizedMatch } from "@voip/utils/normalize";

describe.current.tags("headless");

describe("normalizedMatch", () => {
    test("plain ASCII inputs", () => {
        const { start, end, match } = normalizedMatch("Yuchen (yhu)", "yhu");
        expect(match).toBe("yhu");
        expect(start).toBe(8);
        expect(end).toBe(11);
    });
    test("compatibility equivalence", () => {
        const { start, end, match } = normalizedMatch("𝔖𝔥𝔯𝔢𝔨", "SHRE");
        expect(match).toBe("𝔖𝔥𝔯𝔢");
        expect(start).toBe(0);
        expect(end).toBe(8);
        expect("𝔖𝔥𝔯𝔢𝔨".slice(start, end)).toBe(match);
    });
    test("some fancy letters without canonical decomposition", () => {
        const { start, end, match } = normalizedMatch("Bjørn Dæhlie", "ORN DAE");
        expect(start).toBe(2);
        expect(end).toBe(8);
        expect(match).toBe("ørn Dæ");
    });
    describe("ligatures", () => {
        test("in source string", () => {
            const { start, end, match } = normalizedMatch("Richard Cœur de Lion", "coeur");
            expect(start).toBe(8);
            expect(end).toBe(12);
            expect(match).toBe("Cœur");
        });
        test("in substring", () => {
            const { start, end, match } = normalizedMatch("Džemal Bijedić", "ǆ");
            expect(start).toBe(0);
            expect(end).toBe(2);
            expect(match).toBe("Dž");
        });
        test("substring ends in the middle of a ligature", () => {
            const { start, end, match } = normalizedMatch("Æthelflæd", "aethelfla");
            expect(start).toBe(0);
            expect(end).toBe(8);
            expect(match).toBe("Æthelflæ");
        });
    });
    describe("full case folding", () => {
        test("in source string", () => {
            const { start, end, match } = normalizedMatch("Scleßin", "essi");
            expect(start).toBe(3);
            expect(end).toBe(6);
            expect(match).toBe("eßi");
        });
        test("in substring", () => {
            const { start, end, match } = normalizedMatch("Sclessin", "eßi");
            expect(start).toBe(3);
            expect(end).toBe(7);
            expect(match).toBe("essi");
        });
    });
    describe("diacritics", () => {
        test("accent on last letter", () => {
            const { start, end, match } = normalizedMatch("José Bové", "vé");
            expect(start).toBe(7);
            expect(end).toBe(9);
            expect(match).toBe("vé");
        });
        test("normalization form is preserved", () => {
            const { start, end, match } = normalizedMatch(
                "eĥoŝanĝo ĉiuĵaŭde".normalize("NFD"),
                "EHOSANGO CIUJAUDE"
            );
            expect(start).toBe(0);
            expect(end).toBe(23);
            expect(match).toBe("eĥoŝanĝo ĉiuĵaŭde");
        });
        test("Ph'nglui mglw'nafh Cthulhu R'lyeh wgah'nagl fhtagn", () => {
            const { start, end, match } = normalizedMatch("N̸̟̤̦̥̦͚̘̟̙͓͚̱͇̱͍̦͓͕̝͈̣̺͔̐͂͑̂̅̇̄̏͐̒̾̋̿̀̐̎̄͗̀͋̈́̉̈́͑̋͊̃̃̃͌̃́̚̚͝͝y̸̢̢̢̧͙̳̫̙̺̝͔̭̲̮͎̦͈͉͚̣̖̞̳͙͚͕̪̘̓̓̇͗͑̈͋͑̅̒̎̄̉̊͌̂̈́̏̚͜ͅͅa̶̧̡͕̝̥̝̳̬̙͔̱͎̠̍͌̓͆̾̔̾͐͌̀̔̀̽̓͐̽͒̌̽̀͗͗͋̉̒̒̎͌͘̚̚͜͝͠ř̴͇͒̀̑̊́̓̈́̎̆̈́̾̅̾̈̃̉̂̄͋̄͑̇̃̽̽͌̐̀̉̃̀͛̂̓̄͑͆̋̌̕͘̚̕͘̕͠͝l̷̢͈̙͕͝a̴̧̨̢̧̧̧̨̨̛̛̰̙̹̭̻̘̤̪͎̯͈͙̻͕̜̹̲͎̜͔̻̟͉̾̾͑́̍͆́͛̍̀͛̂͂͑͒͜͝ţ̵̨̩̞̦̺̯̱̝̻̹̜̩͙̮̤̘̟͉͉̘̩̻̠̻̜͖̗̝͓̝͖͚̜̥͍̠̗̰̦̱͔̤̣̮͔̿̓͒̍̈́̀̔̌̐̉͋̌̋͐̅̈́͘͜ȟ̶̢̧̦͔̞̺̮͎̻̣̪̮̣̱̮̤͇͈͖̮̯̝̩̻̄͂͊̈́͂̀̎́̊͌̒̉̊̓̊̀̂̆̋̚͜͠ǫ̸̤̪̜̲̠͕̮͔̜͔͚̺̠̲͇͓̺̣̣̗̭̠̫̓͗̽͋͘͜͠ţ̸̧̨̨̨̛̛̩̫̫̟̣͍̭̯͕̩͖̝̜̱͖͈̯̺̞̬̮̱̲̦͎̠̤̟̖͓͎̹̦̭̖̲̞̱̹̬̯̗͈̓̈́̎͒̒̔̎͑͐͛̄̊͛́̈́̄̾͛̒̒̑́̎͌̌̏̐̑͗̊̈́̀͌̂̏̀́̚͘͝ȩ̴̨̢̛̛̦̥̤̟̣͇̱̜̥̠̦̻̳̼̣̜̺̼̼̝̳͖͙͍̗̦͕̼̟̟̹̹̝̣̮̜͓̜̼̺̺̈́̍̐̽̔́̾̓̔̅̿̽͊̈͒̊̓̔̏̐̐̽̄̈́͑̌̉̉͘͘p̴̡̡̨̧̛̜̫̠͉̜̯͍̩̠̥̩̣̩̲̦̗͚̗̲͕̾̀͗̊̀̊͛̐̽͌̎̊̎̑̍́̓̒̅̉͗̐̿̊̃͋́͂̍͆͂͘̕͜͠", "nya");
            expect(start).toBe(0);
            expect(end).toBe(115);
            expect(match).toBe("N̸̟̤̦̥̦͚̘̟̙͓͚̱͇̱͍̦͓͕̝͈̣̺͔̐͂͑̂̅̇̄̏͐̒̾̋̿̀̐̎̄͗̀͋̈́̉̈́͑̋͊̃̃̃͌̃́̚̚͝͝y̸̢̢̢̧͙̳̫̙̺̝͔̭̲̮͎̦͈͉͚̣̖̞̳͙͚͕̪̘̓̓̇͗͑̈͋͑̅̒̎̄̉̊͌̂̈́̏̚͜ͅͅa");
        });
    });
    describe("corner cases", () => {
        test("empty source string", () => {
            const { start, end, match } = normalizedMatch("", "Œdipe Roi");
            expect(start).toBe(-1);
            expect(end).toBe(-1);
            expect(match).toBe("");
        });
        test("empty substring", () => {
            const { start, end, match } = normalizedMatch("泽龙", "");
            expect(start).toBe(0);
            expect(end).toBe(0);
            expect(match).toBe("");
        });
        test("empty inputs", () => {
            const { start, end, match } = normalizedMatch("", "");
            expect(start).toBe(0);
            expect(end).toBe(0);
            expect(match).toBe("");
        });
        test("matches last character", () => {
            const { start, end, match } = normalizedMatch("雨晨", "晨");
            expect(start).toBe(1);
            expect(end).toBe(2);
            expect(match).toBe("晨");
        });
    });
});

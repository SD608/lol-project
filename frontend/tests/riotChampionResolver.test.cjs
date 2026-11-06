"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function makeResolver(fetchMock) {
  const source = fs.readFileSync(path.join(__dirname, "..", "app", "riotChampionResolver.ts"), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  const sandbox = { module, exports: module.exports, fetch: fetchMock, Map, Promise, Error };
  vm.runInNewContext(compiled, sandbox, { filename: "riotChampionResolver.js" });
  return module.exports;
}

const roster = {
  Caitlyn: { id: "Caitlyn", name: "케이틀린" },
  Tryndamere: { id: "Tryndamere", name: "트린다미어" },
  MissFortune: { id: "MissFortune", name: "미스 포츈" },
  AurelionSol: { id: "AurelionSol", name: "아우렐리온 솔" },
};

test("maps Korean names to official Data Dragon filenames without DB riot_id", async () => {
  let calls = 0;
  const resolver = makeResolver(async (url) => {
    calls += 1;
    assert.match(url, /ko_KR\/champion\.json$/);
    return { ok: true, json: async () => ({ data: roster }) };
  });
  assert.equal(await resolver.resolveChampionId("16.22.1", { name: "케이틀린", riot_id: null }), "Caitlyn");
  assert.equal(await resolver.resolveChampionId("16.22.1", { name: "트린다미어" }), "Tryndamere");
  assert.equal(await resolver.resolveChampionId("16.22.1", { name: "미스포츈" }), "MissFortune");
  assert.equal(await resolver.resolveChampionId("16.22.1", { name: "아우렐리온 솔" }), "AurelionSol");
  assert.equal(calls, 1, "cache the same official patch roster");
});

test("a stale DB id is ignored if the localized name uniquely resolves", async () => {
  const resolver = makeResolver(async () => ({ ok: true, json: async () => ({ data: roster }) }));
  assert.equal(await resolver.resolveChampionId("16.22.1", { name: "케이틀린", riot_id: "Tryndamere" }), "Caitlyn");
});

test("missing and ambiguous matches fail closed, instead of returning an unrelated champion", () => {
  const resolver = makeResolver(async () => ({ ok: true, json: async () => ({ data: roster }) }));
  assert.throws(() => resolver.resolveOfficialChampionId({ name: "존재하지 않는 챔피언" }, roster), /영문 ID를 찾지 못했습니다/);
  const duplicate = { ...roster, OtherCaitlyn: { id: "OtherCaitlyn", name: "케이틀린" } };
  assert.throws(() => resolver.resolveOfficialChampionId({ name: "케이틀린" }, duplicate), /중복/);
});

test("failed roster load does not poison cache", async () => {
  let calls = 0;
  const resolver = makeResolver(async () => {
    calls += 1;
    return calls === 1 ? { ok: false, status: 503 } : { ok: true, json: async () => ({ data: roster }) };
  });
  await assert.rejects(resolver.resolveChampionId("16.22.1", { name: "케이틀린" }), /503/);
  assert.equal(await resolver.resolveChampionId("16.22.1", { name: "케이틀린" }), "Caitlyn");
  assert.equal(calls, 2);
});

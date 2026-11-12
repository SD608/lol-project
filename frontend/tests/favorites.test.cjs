const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const moduleObject = { exports: {} };
const source = fs.readFileSync(path.join(__dirname, '../app/favorites.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
new Function('module', 'exports', compiled)(moduleObject, moduleObject.exports);
const { FAVORITES_KEY, emptyFavorites, parseFavorites, toggleFavorite, saveFavorites, favoriteFirst } = moduleObject.exports;
test('add/remove are independent per lane and do not mutate previous state', () => {
 const empty=emptyFavorites();const top=toggleFavorite(empty,'탑','가렌');const mid=toggleFavorite(top,'미드','가렌');
 assert.deepEqual(empty['탑'],[]);assert.deepEqual(mid['탑'],['가렌']);assert.deepEqual(mid['미드'],['가렌']);
 assert.deepEqual(toggleFavorite(mid,'탑','가렌')['탑'],[]);assert.deepEqual(toggleFavorite(mid,'탑','가렌')['미드'],['가렌']);
});
test('storage round trip restores favorites after reload', () => {
 const values=new Map();const storage={setItem:(key,value)=>values.set(key,value)};
 const favorites=toggleFavorite(emptyFavorites(),'바텀','징크스');assert.equal(saveFavorites(storage,favorites),true);
 assert.deepEqual(parseFavorites(values.get(FAVORITES_KEY)),favorites);
 const removed=toggleFavorite(parseFavorites(values.get(FAVORITES_KEY)),'바텀','징크스');saveFavorites(storage,removed);
 assert.deepEqual(parseFavorites(values.get(FAVORITES_KEY))['바텀'],[]);
});
test('corrupt, unavailable, oversized and incompatible storage fails safely', () => {
 for(const raw of [null,'oops','null','[]','{}','{"version":2,"lanes":{}}','x'.repeat(100001)])assert.deepEqual(parseFavorites(raw),emptyFavorites());
 const parsed=parseFavorites(JSON.stringify({version:1,lanes:{'탑':['가렌','가렌',null,12,{},''],'미드':true}}));
 assert.deepEqual(parsed['탑'],['가렌']);assert.deepEqual(parsed['미드'],[]);
 assert.equal(saveFavorites({setItem(){throw Error('quota');}},emptyFavorites()),false);
});
test('favorites sort first while retaining existing search order, with optional filter', () => {
 const items=[{name:'가렌'},{name:'나르'},{name:'다리우스'}];
 assert.deepEqual(favoriteFirst(items,['다리우스'],false).map(i=>i.name),['다리우스','가렌','나르']);
 assert.deepEqual(favoriteFirst(items,['다리우스'],true).map(i=>i.name),['다리우스']);
 assert.deepEqual(favoriteFirst(items,[],true),[]);assert.deepEqual(items.map(i=>i.name),['가렌','나르','다리우스']);
});

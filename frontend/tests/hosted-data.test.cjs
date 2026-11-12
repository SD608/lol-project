const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const frontendSource = path.resolve(__dirname, '../data/counter-guide-26.22.json');

test('hosted guide includes full directional coverage and evidence counts', () => {
  const guide = JSON.parse(readFileSync(frontendSource, 'utf8'));
  assert.equal(guide.patch, '26.22');
  assert.equal(guide.champions.length, 173);
  assert.equal(Object.values(guide.lanes).reduce((sum, names) => sum + names.length, 0), 266);
  assert.equal(guide.rows.length, 14468);
  assert.equal(guide.rows.filter(row => row.evidence === 'statistical').length, 110);
  assert.equal(guide.rows.filter(row => row.evidence === 'theoretical').length, 14358);
  const seen = new Set(guide.rows.map(row => JSON.stringify([row.lane, row.champion, row.opponent])));
  assert.equal(seen.size, 14468);
  for (const row of guide.rows) {
    assert.ok(seen.has(JSON.stringify([row.lane, row.opponent, row.champion])));
  }
});

test('deployable copy matches backend source byte-for-byte', () => {
  const original = path.resolve(__dirname, '../../data/counter-guide-26.22.json');
  const hash = path => crypto.createHash('sha256').update(readFileSync(path)).digest('hex');
  // Repository CI has both files; Vercel monorepo build may expose only frontend.
  if (require('node:fs').existsSync(original)) {
    assert.equal(hash(frontendSource), hash(original));
  }
});

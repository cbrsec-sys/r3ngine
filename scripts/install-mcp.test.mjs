import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseWrapperArgs } from './install-mcp.mjs';

test('wrapper flags stop at first setup argument', () => {
  const opts = parseWrapperArgs(['--update', '--url', 'https://h', '--yes']);
  assert.equal(opts.update, true);
  assert.deepEqual(opts.rest, ['--url', 'https://h', '--yes']);
});

test('double dash separates wrapper from setup', () => {
  const opts = parseWrapperArgs(['--repo', 'https://git.example/mcp.git', '--', '--transport', 'http']);
  assert.equal(opts.repo, 'https://git.example/mcp.git');
  assert.deepEqual(opts.rest, ['--transport', 'http']);
});

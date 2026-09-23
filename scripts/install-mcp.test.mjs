import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseWrapperArgs, nodeBin, usesCmdShell } from './install-mcp.mjs';

test('wrapper flags stop at first setup argument', () => {
  const opts = parseWrapperArgs(['--update', '--url', 'https://h', '--yes']);
  assert.equal(opts.update, true);
  assert.deepEqual(opts.rest, ['--url', 'https://h', '--yes']);
});

test('wrapper update alone leaves empty rest for setup forwarding', () => {
  const opts = parseWrapperArgs(['--update']);
  assert.equal(opts.update, true);
  assert.deepEqual(opts.rest, []);
});

test('double dash separates wrapper from setup', () => {
  const opts = parseWrapperArgs(['--repo', 'https://git.example/mcp.git', '--', '--transport', 'http']);
  assert.equal(opts.repo, 'https://git.example/mcp.git');
  assert.deepEqual(opts.rest, ['--transport', 'http']);
});

test('nodeBin uses NODE from env, not an absolute install path', () => {
  assert.equal(nodeBin({}), 'node');
  assert.equal(nodeBin({ NODE: 'node' }), 'node');
  assert.equal(usesCmdShell('C:\\Program Files\\nodejs\\node.exe', 'win32'), false);
  assert.equal(usesCmdShell('npm.cmd', 'win32'), true);
  assert.equal(usesCmdShell('npm.cmd', 'linux'), false);
});

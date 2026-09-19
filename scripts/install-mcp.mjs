#!/usr/bin/env node
/**
 * Clone r3ngine-mcp next to this repo (if needed) and run its Node setup script.
 *
 *   node scripts/install-mcp.mjs --url https://host --key r3n_mcp_… --yes
 *   node scripts/install-mcp.mjs --update -- --transport http --detach
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_REPO = 'https://github.com/whiterabb17/r3ngine-mcp.git';
const DEFAULT_DIR = path.join(ROOT, 'r3ngine-mcp');

function log(message) {
  process.stderr.write(`${message}\n`);
}

function run(command, args, cwd = ROOT) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    env: process.env,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed with exit ${result.status}`);
  }
}

function hasGit(dir) {
  return fs.existsSync(path.join(dir, '.git'));
}

function isMcpCheckout(dir) {
  return fs.existsSync(path.join(dir, 'scripts', 'install.mjs'))
    && fs.existsSync(path.join(dir, 'package.json'));
}

export function parseWrapperArgs(argv) {
  const out = {
    repo: process.env.R3NGINE_MCP_REPO || DEFAULT_REPO,
    dir: DEFAULT_DIR,
    update: false,
    help: false,
    rest: [],
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--') {
      out.rest = argv.slice(i + 1);
      break;
    }
    if (arg === '--repo') {
      i += 1;
      out.repo = argv[i];
      continue;
    }
    if (arg === '--dir') {
      i += 1;
      out.dir = path.resolve(argv[i]);
      continue;
    }
    if (arg === '--update') {
      out.update = true;
      continue;
    }
    if (arg === '-h' || arg === '--help') {
      out.help = true;
      continue;
    }
    out.rest = argv.slice(i);
    break;
  }
  return out;
}

function usage() {
  log(`Usage: node scripts/install-mcp.mjs [wrapper options] [--] [setup options]

Wrapper:
  --repo <url>   git remote (default ${DEFAULT_REPO})
  --dir <path>   checkout path (default ./r3ngine-mcp)
  --update       git pull if the checkout already exists

Setup options are forwarded to r3ngine-mcp/scripts/install.mjs
  (e.g. --url --key --transport --yes --write-cursor --detach)
`);
}

export function ensureCheckout({ dir, repo, update }) {
  if (isMcpCheckout(dir)) {
    log(`Using existing r3ngine-mcp at ${dir}`);
    if (update && hasGit(dir)) {
      log('Updating r3ngine-mcp…');
      run('git', ['pull', '--ff-only'], dir);
    }
    return dir;
  }
  if (fs.existsSync(dir)) {
    throw new Error(`${dir} exists but is not an r3ngine-mcp checkout (missing scripts/install.mjs)`);
  }
  log(`Cloning ${repo} → ${dir}`);
  run('git', ['clone', repo, dir]);
  if (!isMcpCheckout(dir)) {
    throw new Error('Clone succeeded but scripts/install.mjs was not found');
  }
  return dir;
}

export function main(argv = process.argv.slice(2)) {
  const opts = parseWrapperArgs(argv);
  if (opts.help) {
    usage();
    return 0;
  }
  const major = Number(String(process.versions.node).split('.')[0]);
  if (!Number.isFinite(major) || major < 20) {
    throw new Error(`Node.js 20+ is required (found ${process.versions.node})`);
  }
  const dir = ensureCheckout(opts);
  const installer = path.join(dir, 'scripts', 'install.mjs');
  log(`Running ${installer}`);
  run(process.execPath, [installer, ...opts.rest], dir);
  return 0;
}

const invoked = Boolean(process.argv[1])
  && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invoked) {
  try {
    process.exit(main() ?? 0);
  } catch (error) {
    log(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

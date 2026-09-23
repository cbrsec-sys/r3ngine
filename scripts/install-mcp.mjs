#!/usr/bin/env node
/**
 * Clone r3ngine-mcp next to this repo (if needed) and run its Node setup script.
 *
 *   node scripts/install-mcp.mjs --url https://host --key r3n_mcp_… --yes
 *   node scripts/install-mcp.mjs --update
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_REPO = 'https://github.com/whiterabb17/r3ngine-mcp.git';
const DEFAULT_DIR = path.join(ROOT, 'r3ngine-mcp');
/** Compose build context for docker compose files (context: ../r3ngine-mcp). */
export const COMPOSE_MCP_CONTEXT = path.resolve(ROOT, '..', 'r3ngine-mcp');

function log(message) {
  process.stderr.write(`${message}\n`);
}

export function nodeBin(env = process.env) {
  return env.NODE || 'node';
}

export function usesCmdShell(command, platform = process.platform) {
  return platform === 'win32' && /\.(cmd|bat)$/i.test(command);
}

function run(command, args, cwd = ROOT) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: 'inherit',
    env: process.env,
    windowsHide: true,
    shell: usesCmdShell(command),
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
    noDocker: false,
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
    if (arg === '--no-docker') {
      out.noDocker = true;
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
  --update       git pull, rebuild local MCP, and rebuild/recreate the Docker MCP
                 container when one already exists for this stack
  --no-docker    with --update, skip Docker image/container refresh

Setup options are forwarded to r3ngine-mcp/scripts/install.mjs
  (e.g. --url --key --transport --yes --write-cursor --detach --stop --restart --update)

Examples:
  node scripts/install-mcp.mjs --url https://host --key r3n_mcp_… --yes --write-cursor
  node scripts/install-mcp.mjs --update
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

/** Prefer `docker compose`, fall back to `docker-compose`. */
export function resolveDockerCompose(exec = spawnSync) {
  const probe = exec('docker', ['compose', 'version'], {
    encoding: 'utf8',
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  if (!probe.error && probe.status === 0) {
    return { command: 'docker', argsPrefix: ['compose'] };
  }
  return { command: 'docker-compose', argsPrefix: [] };
}

/**
 * Locate an existing r3ngine-mcp container and the compose invocation that owns it.
 * Returns null when Docker is unavailable or no MCP container exists.
 */
export function findMcpComposeService({ exec = spawnSync, root = ROOT } = {}) {
  const list = exec(
    'docker',
    ['ps', '-a', '--filter', 'name=r3ngine-mcp', '--format', '{{.ID}}\t{{.Names}}\t{{.Status}}'],
    { encoding: 'utf8', windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] },
  );
  if (list.error || list.status !== 0) return null;
  const line = String(list.stdout || '').trim().split(/\r?\n/).find(Boolean);
  if (!line) return null;
  const [id, name, status = ''] = line.split('\t');
  if (!id || !name) return null;
  const running = /^\s*Up\b/i.test(status);

  const insp = exec('docker', ['inspect', '-f', '{{json .Config.Labels}}', id], {
    encoding: 'utf8',
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let labels = {};
  try {
    labels = JSON.parse(String(insp.stdout || '{}'));
  } catch {
    labels = {};
  }

  const configFiles = String(labels['com.docker.compose.project.config_files'] || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  const project = labels['com.docker.compose.project'] || undefined;
  const workingDir = labels['com.docker.compose.project.working_dir'] || root;
  const service = labels['com.docker.compose.service'] || 'r3ngine-mcp';

  const composeArgs = [];
  if (project) composeArgs.push('-p', project);
  const envFile = path.join(root, '.env');
  if (fs.existsSync(envFile)) composeArgs.push('--env-file', envFile);
  if (configFiles.length) {
    for (const file of configFiles) composeArgs.push('-f', file);
  } else {
    const prod = path.join(root, 'docker', 'docker-compose.yml');
    const dev = path.join(root, 'docker', 'docker-compose.dev.yml');
    if (fs.existsSync(prod)) composeArgs.push('-f', prod);
    else if (fs.existsSync(dev)) composeArgs.push('-f', dev);
  }
  // Prod compose gates the service behind profiles: ["mcp"]; harmless on files without it.
  composeArgs.push('--profile', 'mcp');

  return {
    id,
    name,
    running,
    service,
    cwd: workingDir,
    composeArgs,
    configFiles,
  };
}

export function pullMcpCheckout(dir) {
  if (!isMcpCheckout(dir)) return false;
  if (!hasGit(dir)) return false;
  log(`Updating r3ngine-mcp at ${dir}…`);
  run('git', ['pull', '--ff-only'], dir);
  return true;
}

/**
 * Rebuild the MCP image when a container already exists; recreate only if it was running.
 */
export function updateMcpDockerContainer({
  exec = spawnSync,
  root = ROOT,
  runFn = run,
} = {}) {
  const info = findMcpComposeService({ exec, root });
  if (!info) {
    log('No r3ngine-mcp Docker container found; skipping image rebuild.');
    return { updated: false, recreated: false, reason: 'not-found' };
  }

  const dc = resolveDockerCompose(exec);
  const buildArgs = [...dc.argsPrefix, ...info.composeArgs, 'build', info.service];
  log(`Building Docker image for ${info.service} (${info.name})…`);
  runFn(dc.command, buildArgs, info.cwd);

  if (!info.running) {
    log('MCP image rebuilt (container was not running; left stopped).');
    return { updated: true, recreated: false, name: info.name };
  }

  const upArgs = [
    ...dc.argsPrefix,
    ...info.composeArgs,
    'up',
    '-d',
    '--force-recreate',
    '--no-deps',
    info.service,
  ];
  log(`Recreating MCP container ${info.name}…`);
  runFn(dc.command, upArgs, info.cwd);
  log('MCP container rebuilt and recreated.');
  return { updated: true, recreated: true, name: info.name };
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
  const setupArgs = [...opts.rest];
  // Wrapper --update pulls the checkout; forward --update so the sidecar rebuilds/restarts.
  if (opts.update && !setupArgs.includes('--update')) {
    setupArgs.unshift('--update');
  }

  if (opts.update && !opts.noDocker) {
    // Compose builds from ../r3ngine-mcp (sibling). Pull that tree when it differs from --dir.
    const composeCtx = COMPOSE_MCP_CONTEXT;
    if (path.resolve(composeCtx) !== path.resolve(dir) && isMcpCheckout(composeCtx)) {
      pullMcpCheckout(composeCtx);
    }
    updateMcpDockerContainer({ root: ROOT });
  }

  log(`Running ${installer}`);
  run(nodeBin(), [installer, ...setupArgs], dir);
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

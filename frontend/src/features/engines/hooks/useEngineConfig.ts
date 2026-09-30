import { useState, useCallback, useEffect, useRef } from 'react';
import { dump as yamlDump, load as yamlLoad } from 'js-yaml';
import type { DumpOptions } from 'js-yaml';
import type {
  EngineConfig, SectionKey, GlobalConfig, SpiderfootConfig,
} from '../types/engineConfig';
import { DEFAULT_ENGINE_CONFIG } from '../types/engineConfig';

/**
 * Engine YAML is user-edited, so every value is `unknown` until read: mappings go through
 * `asMapping`, and leaf values are taken at the type the engine schema declares for them.
 */
type YamlMapping = Record<string, unknown>;

function isMapping(node: unknown): node is YamlMapping {
  return typeof node === 'object' && node !== null && !Array.isArray(node);
}

/** A YAML mapping node, or `{}` for a missing/null node or a list. */
function asMapping(node: unknown): YamlMapping {
  return isMapping(node) ? node : {};
}

/** Secret scanning settings from all three spellings, oldest first so the newest wins. */
function secretScanningSettings(raw: YamlMapping): YamlMapping {
  return {
    ...asMapping(asMapping(raw.osint).leaks_and_secrets),
    ...asMapping(raw.leaks_and_secrets),
    ...asMapping(raw.secret_scanning),
  };
}

// ─── Keys the form owns ──────────────────────────────────────────────────────

/**
 * The keys of a YAML mapping the form owns. `null`: the form owns the whole value.
 * A nested `OwnedKeys`: the form owns that mapping's listed keys and carries the rest.
 */
export interface OwnedKeys {
  readonly [key: string]: OwnedKeys | null;
}

const owned = (...keys: string[]): OwnedKeys => Object.fromEntries(keys.map((key) => [key, null]));

const VIGOLIUM_STAGE = ['strategy', 'concurrency', 'rate_limit', 'timeout'];

/**
 * Everything the parser reads or the serialiser may write, per mapping. A key missing
 * from the loaded YAML's mapping here is carried through a save unchanged, so every key
 * the form can leave out (a disabled section, a default global, an option written only
 * when switched on) must be listed or a stale value comes back from the old YAML.
 */
export const FORM_OWNED_KEYS: Readonly<Record<SectionKey | keyof GlobalConfig | 'secret_scanning', OwnedKeys | null>> = {
  custom_headers: null,
  enable_http_crawl: null,
  threads: null,
  timeout: null,
  rate_limit: null,
  retries: null,
  intensity: null,

  subdomain_discovery: owned(
    'uses_tools', 'threads', 'timeout', 'enable_http_crawl',
    'use_subfinder_config', 'use_amass_config', 'amass_wordlist',
  ),
  dns_security: owned('enable_axfr', 'enable_dnssec_check', 'enable_dns_brute', 'amplification_threshold'),
  // whatbreach is a boolean or a mapping depending on a checkbox, so it is owned whole.
  osint: {
    ...owned('discover', 'dorks', 'custom_dorks', 'intensity', 'documents_limit', 'whatbreach', 'credspy'),
    // gitleaks/trufflehog here are an older spelling of secret_scanning and are carried through.
    leaks_and_secrets: owned('leaklookup', 'leaksearch'),
  },
  spiderfoot_scan: owned('modules', 'intensity', 'threads'),
  vigolium_harvest: owned('run_vigolium_harvest', ...VIGOLIUM_STAGE),
  vigolium_discovery: owned('run_vigolium_discovery', ...VIGOLIUM_STAGE),
  firewall_vpn_scan: owned('run_ike_scan', 'run_sslscan', 'enable_testssl', 'enable_crt_sh', 'ports'),
  http_crawl: owned('threads', 'follow_redirect'),
  port_scan: owned(
    'ports', 'rate_limit', 'threads', 'timeout', 'passive', 'enable_http_crawl',
    'enable_nmap', 'nmap_cmd', 'nmap_script', 'nmap_script_args', 'exclude_ports', 'exclude_subdomains',
    'enable_network_enum',
  ),
  email_security: {
    enabled: null,
    mailbox_verification: owned('enabled', 'timeout', 'max_candidates', 'delay_ms', 'http_url'),
  },
  screenshot: owned(),
  fetch_url: owned(
    'uses_tools', 'remove_duplicate_endpoints', 'duplicate_fields', 'enable_http_crawl',
    'gf_patterns', 'ignore_file_extensions', 'threads',
  ),
  web_api_discovery: owned(
    'uses_tools', 'scan_only_active', 'threads', 'timeout', 'kr_wordlist',
    'run_favirecon', 'run_sourcemapper', 'run_grpcurl', 'run_julius', 'run_gqlspection',
  ),
  param_discovery: owned('enabled', 'min_confidence'),
  dir_file_fuzz: owned(
    'run_ffuf', 'run_dirsearch', 'run_feroxbuster', 'auto_calibration', 'enable_http_crawl', 'extensions',
    'wordlist_name', 'rate_limit', 'threads', 'timeout', 'max_time', 'recursive_level',
    'match_http_status', 'follow_redirect', 'stop_on_error', 'max_repeat_by_signature',
  ),
  waf_detection: owned('enable_http_crawl', 'use_shodan', 'use_censys'),
  waf_bypass: owned('enabled', 'use_benchmarking', 'use_nuclei'),
  // Read under three spellings, written only as secret_scanning; see secretScanningSettings.
  leaks_and_secrets: null,
  // Breach lookups are OSINT settings; the old spellings put them here, where nothing reads them.
  secret_scanning: owned('gitleaks', 'trufflehog', 'betterleaks', 'leaklookup', 'leaksearch'),
  vigolium_analysis: owned('run_vigolium_analysis', ...VIGOLIUM_STAGE),
  vulnerability_scan: {
    ...owned(
      'run_nuclei', 'run_dalfox', 'run_crlfuzz', 'run_s3scanner', 'run_acunetix', 'run_wpscan',
      'run_wptaint_scan', 'run_smugglex', 'run_second_order', 'run_nuclei_dast', 'run_vigolium',
      'run_semgrep', 'run_post_scan_processing', 'concurrency', 'rate_limit', 'retries', 'timeout', 'intensity', 'fetch_gpt_report',
      'enable_http_crawl', 'wpscan_enumeration', 'wpscan_detection_mode',
    ),
    acunetix: owned('submit_live_subdomains', 'resubmit_after_days', 'start_scan_on_submit'),
    nuclei: owned('use_nuclei_config', 'severities', 'tags', 'templates', 'custom_templates'),
    cpanel_scanner: owned('run_cpanel2shell', 'cpanel_user_wordlist', 'proxy_type'),
    react_scanner: owned('run_react2shell'),
    vigolium: owned(
      ...VIGOLIUM_STAGE, 'run_phase_a', 'run_phase_b', 'scope_origin', 'skip_spidering',
    ),
  },
  attack_path_modeling: owned('enabled', 'top_n'),
  tier_7: owned('high_noise_modules'),
  vigolium_audit: owned('run_vigolium_audit', 'intensity', 'use_ai', 'timeout'),
};

/** The parts of a loaded YAML mapping the form does not own. */
interface Leftovers {
  /** Keys the form does not own, with their loaded values. */
  values: YamlMapping;
  /** Leftovers inside the mappings the form owns, by key. */
  nested: Readonly<Record<string, Leftovers>>;
}

const NO_LEFTOVERS: Leftovers = { values: {}, nested: {} };

function collectLeftovers(node: YamlMapping, ownedKeys: OwnedKeys): Leftovers {
  const entries = Object.entries(node);
  return {
    values: Object.fromEntries(entries.filter(([key]) => !Object.hasOwn(ownedKeys, key))),
    nested: Object.fromEntries(entries.flatMap(([key, value]) => {
      const inner = Object.hasOwn(ownedKeys, key) ? ownedKeys[key] : null;
      return inner ? [[key, collectLeftovers(asMapping(value), inner)]] : [];
    })),
  };
}

function engineLeftovers(yamlStr: string): Leftovers {
  const raw = asMapping(yamlLoad(yamlStr));
  return collectLeftovers({ ...raw, secret_scanning: secretScanningSettings(raw) }, FORM_OWNED_KEYS);
}

/**
 * Lays the leftovers under what the form wrote. Only mappings the form actually wrote
 * take nested leftovers: an owned key the form left out stays out, with its leftovers.
 */
function withLeftovers(written: YamlMapping, leftovers: Leftovers): YamlMapping {
  const carried = Object.entries(leftovers.values).filter(([key]) => !Object.hasOwn(written, key));
  const nested = Object.entries(leftovers.nested).flatMap(([key, inner]) => {
    const value = Object.hasOwn(written, key) ? written[key] : undefined;
    return isMapping(value) ? [[key, withLeftovers(value, inner)]] : [];
  });
  // Object spread defines own properties, so a `__proto__` key from the YAML stays a plain key.
  return { ...written, ...Object.fromEntries(carried), ...Object.fromEntries(nested) };
}

// ─── Serialiser ──────────────────────────────────────────────────────────────

/** Writes the form's config, then carries over the loaded YAML's keys the form does not own. */
export function serialiseConfigToYaml(config: EngineConfig, leftovers: Leftovers = NO_LEFTOVERS): string {
  const out: YamlMapping = {};

  // Global fields — top level, no wrapper key
  const g = config.global;
  if (g.custom_headers.length > 0) out.custom_headers = g.custom_headers;
  if (!g.enable_http_crawl) out.enable_http_crawl = false; // only write when non-default
  out.threads = g.threads;
  out.timeout = g.timeout;
  out.rate_limit = g.rate_limit;
  out.retries = g.retries;
  if (g.intensity !== 'normal') out.intensity = g.intensity;

  // Helper: write a section if enabled
  function writeSection(key: string, data: Record<string, unknown>) {
    out[key] = data;
  }

  // ── Tier 1 ──────────────────────────────────────────────────────────────
  if (config.subdomain_discovery.enabled) {
    const c = config.subdomain_discovery.config;
    const s: Record<string, unknown> = { uses_tools: c.uses_tools, threads: c.threads, timeout: c.timeout, enable_http_crawl: c.enable_http_crawl };
    if (c.use_subfinder_config) s.use_subfinder_config = true;
    if (c.use_amass_config) s.use_amass_config = true;
    if (c.amass_wordlist) s.amass_wordlist = c.amass_wordlist;
    writeSection('subdomain_discovery', s);
  }

  if (config.dns_security.enabled) {
    const c = config.dns_security.config;
    writeSection('dns_security', {
      enable_axfr: c.enable_axfr, enable_dnssec_check: c.enable_dnssec_check,
      enable_dns_brute: c.enable_dns_brute, amplification_threshold: c.amplification_threshold,
    });
  }

  if (config.osint.enabled) {
    const c = config.osint.config;
    writeSection('osint', {
      discover: c.discover,
      dorks: c.dorks,
      ...(c.custom_dorks.length > 0 ? { custom_dorks: c.custom_dorks } : {}),
      intensity: c.intensity,
      documents_limit: c.documents_limit,
      // whatbreach: nested dict when download enabled, plain boolean otherwise
      whatbreach: c.whatbreach
        ? (c.whatbreach_download_databases ? { download_found_databases: true } : true)
        : false,
      credspy: c.credspy,
      leaks_and_secrets: { leaklookup: c.leaklookup, leaksearch: c.leaksearch },
    });
  }

  if (config.spiderfoot_scan.enabled) {
    const c = config.spiderfoot_scan.config;
    writeSection('spiderfoot_scan', { modules: c.modules, intensity: c.intensity, threads: c.threads });
  }

  if (!config.vigolium_harvest.enabled) {
    writeSection('vigolium_harvest', { run_vigolium_harvest: false });
  } else {
    const c = config.vigolium_harvest.config;
    writeSection('vigolium_harvest', { run_vigolium_harvest: true, strategy: c.strategy, concurrency: c.concurrency, rate_limit: c.rate_limit, timeout: c.timeout });
  }

  if (!config.vigolium_discovery.enabled) {
    writeSection('vigolium_discovery', { run_vigolium_discovery: false });
  } else {
    const c = config.vigolium_discovery.config;
    writeSection('vigolium_discovery', { run_vigolium_discovery: true, strategy: c.strategy, concurrency: c.concurrency, rate_limit: c.rate_limit, timeout: c.timeout });
  }

  if (config.firewall_vpn_scan.enabled) {
    const c = config.firewall_vpn_scan.config;
    writeSection('firewall_vpn_scan', {
      run_ike_scan: c.run_ike_scan, run_sslscan: c.run_sslscan,
      enable_testssl: c.enable_testssl, enable_crt_sh: c.enable_crt_sh, ports: c.ports,
    });
  }

  // ── Tier 2 ──────────────────────────────────────────────────────────────
  if (config.http_crawl.enabled) {
    const c = config.http_crawl.config;
    writeSection('http_crawl', { threads: c.threads, follow_redirect: c.follow_redirect });
  }

  if (config.port_scan.enabled) {
    const c = config.port_scan.config;
    const s: Record<string, unknown> = {
      ports: c.ports, rate_limit: c.rate_limit, threads: c.threads, timeout: c.timeout,
      passive: c.passive, enable_http_crawl: c.enable_http_crawl,
    };
    if (c.enable_nmap) {
      s.enable_nmap = true;
      if (c.nmap_cmd) s.nmap_cmd = c.nmap_cmd;
      if (c.nmap_script) s.nmap_script = c.nmap_script;
      if (c.nmap_script_args) s.nmap_script_args = c.nmap_script_args;
    }
    if (c.exclude_ports.length > 0) s.exclude_ports = c.exclude_ports;
    if (c.exclude_subdomains) s.exclude_subdomains = true;
    s.enable_network_enum = c.enable_network_enum;
    writeSection('port_scan', s);
  }

  // Always written: a missing email_security section means "on" to the backend,
  // so switching it off has to be explicit.
  {
    const c = config.email_security.config;
    const mv: Record<string, unknown> = {
      enabled: c.mailbox_verification, timeout: c.timeout,
      max_candidates: c.max_candidates, delay_ms: c.delay_ms,
    };
    if (c.http_url) mv.http_url = c.http_url;
    writeSection('email_security', { enabled: config.email_security.enabled, mailbox_verification: mv });
  }

  if (config.screenshot.enabled) writeSection('screenshot', {});

  // ── Tier 3+4 ────────────────────────────────────────────────────────────
  if (config.fetch_url.enabled) {
    const c = config.fetch_url.config;
    writeSection('fetch_url', {
      uses_tools: c.uses_tools, remove_duplicate_endpoints: c.remove_duplicate_endpoints,
      duplicate_fields: c.duplicate_fields, enable_http_crawl: c.enable_http_crawl,
      gf_patterns: c.gf_patterns, ignore_file_extensions: c.ignore_file_extensions, threads: c.threads,
    });
  }

  if (config.web_api_discovery.enabled) {
    const c = config.web_api_discovery.config;
    writeSection('web_api_discovery', {
      uses_tools: c.uses_tools, scan_only_active: c.scan_only_active,
      threads: c.threads, timeout: c.timeout, kr_wordlist: c.kr_wordlist,
      run_favirecon: c.run_favirecon, run_sourcemapper: c.run_sourcemapper,
      run_grpcurl: c.run_grpcurl, run_julius: c.run_julius, run_gqlspection: c.run_gqlspection,
    });
  }

  if (config.param_discovery.enabled) {
    writeSection('param_discovery', { enabled: true, min_confidence: config.param_discovery.config.min_confidence });
  }

  if (config.dir_file_fuzz.enabled) {
    const c = config.dir_file_fuzz.config;
    writeSection('dir_file_fuzz', {
      run_ffuf: c.run_ffuf, run_dirsearch: c.run_dirsearch, run_feroxbuster: c.run_feroxbuster,
      auto_calibration: c.auto_calibration, enable_http_crawl: c.enable_http_crawl,
      extensions: c.extensions, wordlist_name: c.wordlist_name,
      rate_limit: c.rate_limit, threads: c.threads, timeout: c.timeout,
      max_time: c.max_time, recursive_level: c.recursive_level,
      match_http_status: c.match_http_status, follow_redirect: c.follow_redirect,
      stop_on_error: c.stop_on_error, max_repeat_by_signature: c.max_repeat_by_signature,
    });
  }

  // ── Tier 5 ──────────────────────────────────────────────────────────────
  if (config.waf_detection.enabled) {
    const c = config.waf_detection.config;
    writeSection('waf_detection', { enable_http_crawl: c.enable_http_crawl, use_shodan: c.use_shodan, use_censys: c.use_censys });
  }

  if (config.waf_bypass.enabled) {
    const c = config.waf_bypass.config;
    writeSection('waf_bypass', { enabled: true, use_benchmarking: c.use_benchmarking, use_nuclei: c.use_nuclei });
  }

  if (config.leaks_and_secrets.enabled) {
    const c = config.leaks_and_secrets.config;
    // secret_scanning is the key the scan workflows gate on; the UI section keeps its old name.
    writeSection('secret_scanning', { gitleaks: c.gitleaks, trufflehog: c.trufflehog, betterleaks: c.betterleaks });
  }

  if (!config.vigolium_analysis.enabled) {
    writeSection('vigolium_analysis', { run_vigolium_analysis: false });
  } else {
    const c = config.vigolium_analysis.config;
    writeSection('vigolium_analysis', { run_vigolium_analysis: true, strategy: c.strategy, concurrency: c.concurrency, rate_limit: c.rate_limit, timeout: c.timeout });
  }

  // ── Tier 6 ──────────────────────────────────────────────────────────────
  if (config.vulnerability_scan.enabled) {
    const c = config.vulnerability_scan.config;
    const s: Record<string, unknown> = {
      run_nuclei: c.run_nuclei, run_dalfox: c.run_dalfox, run_crlfuzz: c.run_crlfuzz,
      run_s3scanner: c.run_s3scanner, run_acunetix: c.run_acunetix, run_wpscan: c.run_wpscan,
      run_wptaint_scan: c.run_wptaint_scan, run_smugglex: c.run_smugglex,
      run_second_order: c.run_second_order, run_nuclei_dast: c.run_nuclei_dast,
      run_vigolium: c.run_vigolium, run_semgrep: c.run_semgrep,
      run_post_scan_processing: c.run_post_scan_processing,
      concurrency: c.concurrency, rate_limit: c.rate_limit, retries: c.retries,
      timeout: c.timeout, intensity: c.intensity, fetch_gpt_report: c.fetch_gpt_report,
      enable_http_crawl: c.enable_http_crawl,
    };
    if (c.run_wpscan) {
      s.wpscan_enumeration = c.wpscan_enumeration;
      s.wpscan_detection_mode = c.wpscan_detection_mode;
    }
    if (c.run_nuclei) s.nuclei = { use_nuclei_config: c.nuclei.use_nuclei_config, severities: c.nuclei.severities, ...(c.nuclei.tags.length ? { tags: c.nuclei.tags } : {}), ...(c.nuclei.templates.length ? { templates: c.nuclei.templates } : {}), ...(c.nuclei.custom_templates.length ? { custom_templates: c.nuclei.custom_templates } : {}) };
    s.react_scanner = { run_react2shell: c.run_react2shell };
    s.cpanel_scanner = { run_cpanel2shell: c.cpanel_scanner.run_cpanel2shell, cpanel_user_wordlist: c.cpanel_scanner.cpanel_user_wordlist, proxy_type: c.cpanel_scanner.proxy_type };
    if (c.run_vigolium) s.vigolium = { strategy: c.vigolium.strategy, concurrency: c.vigolium.concurrency, rate_limit: c.vigolium.rate_limit, timeout: c.vigolium.timeout, run_phase_a: c.vigolium.run_phase_a, run_phase_b: c.vigolium.run_phase_b, scope_origin: c.vigolium.scope_origin, skip_spidering: c.vigolium.skip_spidering };
    // Tier-2 live-subdomain submission — independent of run_acunetix (Tier 6).
    // Must round-trip or submit_live_subdomains never reaches the backend.
    if (c.acunetix) {
      s.acunetix = {
        submit_live_subdomains: !!c.acunetix.submit_live_subdomains,
        resubmit_after_days: c.acunetix.resubmit_after_days ?? 3,
        start_scan_on_submit: !!c.acunetix.start_scan_on_submit,
      };
    }
    writeSection('vulnerability_scan', s);
  }

  // ── Tier 7 ──────────────────────────────────────────────────────────────
  // A missing section runs APME, so switching it off is written explicitly.
  writeSection('attack_path_modeling', config.attack_path_modeling.enabled
    ? { enabled: true, top_n: config.attack_path_modeling.config.top_n }
    : { enabled: false });

  if (config.tier_7.enabled) {
    writeSection('tier_7', { high_noise_modules: config.tier_7.config.high_noise_modules });
  }

  if (!config.vigolium_audit.enabled) {
    writeSection('vigolium_audit', { run_vigolium_audit: false });
  } else {
    const c = config.vigolium_audit.config;
    writeSection('vigolium_audit', { run_vigolium_audit: true, intensity: c.intensity, use_ai: c.use_ai, timeout: c.timeout });
  }

  return yamlDump(withLeftovers(out, leftovers), { lineWidth: 120, quotingType: "'", forceQuotes: false } as DumpOptions);
}

// ─── Parser ──────────────────────────────────────────────────────────────────

/** Scanner keys that mark a leaks_and_secrets mapping as secret-scanning settings. */
const SECRET_SCANNERS = ['gitleaks', 'trufflehog', 'betterleaks'];

/** SpiderFoot reads normal / fast / deep; older engines saved light / aggressive. */
function spiderfootIntensity(value: unknown): SpiderfootConfig['intensity'] {
  if (value === 'fast' || value === 'light') return 'fast';
  if (value === 'deep' || value === 'aggressive') return 'deep';
  return 'normal';
}

function parseYamlToConfig(yamlStr: string): EngineConfig {
  const doc: unknown = yamlLoad(yamlStr);
  if (doc !== null && doc !== undefined && typeof doc !== 'object') {
    throw new Error('Engine configuration must be a YAML mapping');
  }
  const raw = asMapping(doc);
  const def = DEFAULT_ENGINE_CONFIG;

  const mergedLeaks = secretScanningSettings(raw);

  const g = def.global;
  type GlobalConfig = EngineConfig['global'];
  const globalValue = <K extends keyof GlobalConfig>(key: K, fallback: GlobalConfig[K]): GlobalConfig[K] =>
    (raw[key] as GlobalConfig[K] | undefined) ?? fallback;
  const global: GlobalConfig = {
    threads: globalValue('threads', g.threads),
    timeout: globalValue('timeout', g.timeout),
    rate_limit: globalValue('rate_limit', g.rate_limit),
    retries: globalValue('retries', g.retries),
    intensity: globalValue('intensity', g.intensity),
    custom_headers: globalValue('custom_headers', []),
    enable_http_crawl: globalValue('enable_http_crawl', g.enable_http_crawl),
  };

  // The backend runs these steps unless their flag is false, so a missing section
  // is on and switching the card off has to write the flag.
  function runFlagSection<T>(key: string, flag: string, map: (r: YamlMapping) => T): { enabled: boolean; config: T } {
    const r = asMapping(raw[key]);
    return { enabled: r[flag] !== false, config: map(r) };
  }

  function section<T>(key: string, map: (r: YamlMapping) => T, defConfig: T): { enabled: boolean; config: T } {
    const present = key in raw && raw[key] !== null;
    const r = present ? asMapping(raw[key]) : {};
    return { enabled: present, config: present ? map(r) : defConfig };
  }

  return {
    global,

    subdomain_discovery: section('subdomain_discovery', (r) => ({
      uses_tools: (r.uses_tools as string[]) ?? def.subdomain_discovery.config.uses_tools,
      threads: (r.threads as number) ?? def.subdomain_discovery.config.threads,
      timeout: (r.timeout as number) ?? def.subdomain_discovery.config.timeout,
      enable_http_crawl: (r.enable_http_crawl as boolean) ?? true,
      use_subfinder_config: (r.use_subfinder_config as boolean) ?? false,
      use_amass_config: (r.use_amass_config as boolean) ?? false,
      amass_wordlist: (r.amass_wordlist as string) ?? '',
    }), def.subdomain_discovery.config) as EngineConfig['subdomain_discovery'],

    dns_security: {
      enabled: 'dns_security' in raw,
      config: (() => {
        const r = asMapping(raw.dns_security);
        const d = def.dns_security.config;
        return {
          enable_axfr: (r.enable_axfr as boolean) ?? d.enable_axfr,
          enable_dnssec_check: (r.enable_dnssec_check as boolean) ?? d.enable_dnssec_check,
          enable_dns_brute: (r.enable_dns_brute as boolean) ?? d.enable_dns_brute,
          amplification_threshold: (r.amplification_threshold as number) ?? d.amplification_threshold,
        };
      })(),
    },

    osint: section('osint', (r) => ({
      discover: (r.discover as string[]) ?? def.osint.config.discover,
      dorks: (r.dorks as string[]) ?? def.osint.config.dorks,
      custom_dorks: (r.custom_dorks as string[]) ?? [],
      intensity: (r.intensity as 'normal' | 'aggressive' | 'light') ?? 'normal',
      documents_limit: (r.documents_limit as number) ?? 50,
      // whatbreach can be boolean true or { download_found_databases: true }
      ...(() => {
        const wb = r.whatbreach;
        return {
          whatbreach: wb !== false && wb !== undefined,
          whatbreach_download_databases:
            typeof wb === 'object' && wb !== null
              ? (wb as Record<string, unknown>).download_found_databases === true
              : false,
        };
      })(),
      credspy: (r.credspy as boolean) ?? false,
      // Only osint.leaks_and_secrets runs these; the other spellings never did.
      leaklookup: (asMapping(r.leaks_and_secrets).leaklookup as boolean) ?? false,
      leaksearch: (asMapping(r.leaks_and_secrets).leaksearch as boolean) ?? false,
    }), def.osint.config) as EngineConfig['osint'],

    spiderfoot_scan: section('spiderfoot_scan', (r) => ({
      modules: (r.modules as string) ?? 'all',
      intensity: spiderfootIntensity(r.intensity),
      threads: (r.threads as number) ?? 10,
    }), def.spiderfoot_scan.config) as EngineConfig['spiderfoot_scan'],

    vigolium_harvest: runFlagSection('vigolium_harvest', 'run_vigolium_harvest', (r) => ({
      strategy: (r.strategy as 'fast' | 'balanced' | 'thorough') ?? 'balanced',
      concurrency: (r.concurrency as number) ?? 20,
      rate_limit: (r.rate_limit as number) ?? 50,
      timeout: (r.timeout as string) ?? '10s',
    })) as EngineConfig['vigolium_harvest'],

    vigolium_discovery: runFlagSection('vigolium_discovery', 'run_vigolium_discovery', (r) => ({
      strategy: (r.strategy as 'fast' | 'balanced' | 'thorough') ?? 'balanced',
      concurrency: (r.concurrency as number) ?? 20,
      rate_limit: (r.rate_limit as number) ?? 50,
      timeout: (r.timeout as string) ?? '10s',
    })) as EngineConfig['vigolium_discovery'],

    firewall_vpn_scan: section('firewall_vpn_scan', (r) => ({
      run_ike_scan: (r.run_ike_scan as boolean) ?? true,
      run_sslscan: (r.run_sslscan as boolean) ?? true,
      enable_testssl: (r.enable_testssl as boolean) ?? false,
      enable_crt_sh: (r.enable_crt_sh as boolean) ?? false,
      ports: (r.ports as number[]) ?? [443, 4444, 8443, 10443, 5443],
    }), def.firewall_vpn_scan.config) as EngineConfig['firewall_vpn_scan'],

    http_crawl: section('http_crawl', (r) => ({
      threads: (r.threads as number) ?? 30,
      follow_redirect: (r.follow_redirect as boolean) ?? true,
    }), def.http_crawl.config) as EngineConfig['http_crawl'],

    port_scan: section('port_scan', (r) => ({
      ports: (r.ports as string[]) ?? ['top-100'],
      rate_limit: (r.rate_limit as number) ?? 150,
      threads: (r.threads as number) ?? 30,
      timeout: (r.timeout as number) ?? 5,
      passive: (r.passive as boolean) ?? false,
      enable_http_crawl: (r.enable_http_crawl as boolean) ?? true,
      enable_nmap: (r.enable_nmap as boolean) ?? false,
      nmap_cmd: (r.nmap_cmd as string) ?? '',
      nmap_script: (r.nmap_script as string) ?? '',
      nmap_script_args: (r.nmap_script_args as string) ?? '',
      exclude_ports: (r.exclude_ports as string[]) ?? [],
      exclude_subdomains: (r.exclude_subdomains as boolean) ?? false,
      enable_network_enum: (r.enable_network_enum as boolean) ?? false,
    }), def.port_scan.config) as EngineConfig['port_scan'],

    // Mirrors task_plan.email_security_enabled / parse_mailbox_config: anything but an
    // explicit falsy `enabled` inside a mapping leaves the step on.
    email_security: (() => {
      const r = asMapping(raw.email_security);
      const mv = asMapping(r.mailbox_verification);
      const on = (v: unknown) => v === undefined || Boolean(v);
      const d = def.email_security.config;
      return {
        enabled: on(r.enabled),
        config: {
          mailbox_verification: on(mv.enabled),
          timeout: (mv.timeout as number) ?? d.timeout,
          max_candidates: (mv.max_candidates as number) ?? d.max_candidates,
          delay_ms: (mv.delay_ms as number) ?? d.delay_ms,
          http_url: (mv.http_url as string) ?? d.http_url,
        },
      };
    })(),

    screenshot: { enabled: 'screenshot' in raw && raw.screenshot !== null, config: {} },

    fetch_url: section('fetch_url', (r) => ({
      uses_tools: (r.uses_tools as string[]) ?? def.fetch_url.config.uses_tools,
      remove_duplicate_endpoints: (r.remove_duplicate_endpoints as boolean) ?? true,
      duplicate_fields: (r.duplicate_fields as string[]) ?? ['content_length', 'page_title'],
      enable_http_crawl: (r.enable_http_crawl as boolean) ?? true,
      gf_patterns: (r.gf_patterns as string[]) ?? def.fetch_url.config.gf_patterns,
      ignore_file_extensions: (r.ignore_file_extensions as string[]) ?? def.fetch_url.config.ignore_file_extensions,
      threads: (r.threads as number) ?? 30,
    }), def.fetch_url.config) as EngineConfig['fetch_url'],

    web_api_discovery: section('web_api_discovery', (r) => {
      const tools = (r.uses_tools as string[]) ?? def.web_api_discovery.config.uses_tools;
      // The backend runs a tool when it is listed OR its run_<tool> flag is true,
      // so an absent flag mirrors the list instead of switching the tool on.
      const flag = (key: string, tool: string) => (r[key] as boolean | undefined) ?? tools.includes(tool);
      return {
        uses_tools: tools,
        scan_only_active: (r.scan_only_active as boolean) ?? true,
        threads: (r.threads as number) ?? 30,
        timeout: (r.timeout as number) ?? 5,
        kr_wordlist: (r.kr_wordlist as string) ?? 'routes-small.kite',
        run_favirecon: flag('run_favirecon', 'favirecon'),
        run_sourcemapper: flag('run_sourcemapper', 'sourcemapper'),
        run_grpcurl: flag('run_grpcurl', 'grpcurl'),
        run_julius: flag('run_julius', 'julius'),
        run_gqlspection: flag('run_gqlspection', 'gqlspection'),
      };
    }, def.web_api_discovery.config) as EngineConfig['web_api_discovery'],

    param_discovery: section('param_discovery', (r) => ({
      min_confidence: (r.min_confidence as number) ?? 50,
    }), def.param_discovery.config) as EngineConfig['param_discovery'],

    dir_file_fuzz: section('dir_file_fuzz', (r) => ({
      run_ffuf: (r.run_ffuf as boolean) ?? true,
      run_dirsearch: (r.run_dirsearch as boolean) ?? false,
      run_feroxbuster: (r.run_feroxbuster as boolean) ?? false,
      auto_calibration: (r.auto_calibration as boolean) ?? true,
      enable_http_crawl: (r.enable_http_crawl as boolean) ?? true,
      extensions: (r.extensions as string[]) ?? def.dir_file_fuzz.config.extensions,
      wordlist_name: (r.wordlist_name as string) ?? 'dicc',
      rate_limit: (r.rate_limit as number) ?? 150,
      threads: (r.threads as number) ?? 30,
      timeout: (r.timeout as number) ?? 5,
      max_time: (r.max_time as number) ?? 300,
      recursive_level: (r.recursive_level as number) ?? 2,
      match_http_status: (r.match_http_status as number[]) ?? [200, 204],
      follow_redirect: (r.follow_redirect as boolean) ?? false,
      stop_on_error: (r.stop_on_error as boolean) ?? false,
      max_repeat_by_signature: (r.max_repeat_by_signature as number) ?? 10,
    }), def.dir_file_fuzz.config) as EngineConfig['dir_file_fuzz'],

    waf_detection: section('waf_detection', (r) => ({
      enable_http_crawl: (r.enable_http_crawl as boolean) ?? true,
      use_shodan: (r.use_shodan as boolean) ?? true,
      use_censys: (r.use_censys as boolean) ?? true,
    }), def.waf_detection.config) as EngineConfig['waf_detection'],

    waf_bypass: section('waf_bypass', (r) => ({
      use_benchmarking: (r.use_benchmarking as boolean) ?? true,
      use_nuclei: (r.use_nuclei as boolean) ?? true,
    }), def.waf_bypass.config) as EngineConfig['waf_bypass'],

    leaks_and_secrets: {
      // osint.leaks_and_secrets also holds OSINT's breach lookups, so it only turns this
      // section on when it carries scanner settings (the oldest spelling of this section).
      enabled: 'secret_scanning' in raw || 'leaks_and_secrets' in raw
        || SECRET_SCANNERS.some((k) => k in asMapping(asMapping(raw.osint).leaks_and_secrets)),
      config: {
        gitleaks: (mergedLeaks.gitleaks as boolean) ?? true,
        trufflehog: (mergedLeaks.trufflehog as boolean) ?? true,
        betterleaks: (mergedLeaks.betterleaks as boolean) ?? false,
      },
    },

    vigolium_analysis: runFlagSection('vigolium_analysis', 'run_vigolium_analysis', (r) => ({
      strategy: (r.strategy as 'fast' | 'balanced' | 'thorough') ?? 'balanced',
      concurrency: (r.concurrency as number) ?? 20,
      rate_limit: (r.rate_limit as number) ?? 50,
      timeout: (r.timeout as string) ?? '10s',
    })) as EngineConfig['vigolium_analysis'],

    vulnerability_scan: section('vulnerability_scan', (r) => {
      type VulnScan = EngineConfig['vulnerability_scan']['config'];
      const n = asMapping(r.nuclei) as Partial<VulnScan['nuclei']>;
      const cp = asMapping(r.cpanel_scanner) as Partial<VulnScan['cpanel_scanner']>;
      const vig = asMapping(r.vigolium) as Partial<VulnScan['vigolium']>;
      const ac = asMapping(r.acunetix) as Partial<NonNullable<VulnScan['acunetix']>>;
      return {
        run_nuclei: (r.run_nuclei as boolean) ?? true,
        run_dalfox: (r.run_dalfox as boolean) ?? false,
        run_crlfuzz: (r.run_crlfuzz as boolean) ?? false,
        run_s3scanner: (r.run_s3scanner as boolean) ?? true,
        run_acunetix: (r.run_acunetix as boolean) ?? true,
        run_wpscan: (r.run_wpscan as boolean) ?? true,
        run_wptaint_scan: (r.run_wptaint_scan as boolean) ?? true,
        run_smugglex: (r.run_smugglex as boolean) ?? true,
        run_second_order: (r.run_second_order as boolean) ?? true,
        run_nuclei_dast: (r.run_nuclei_dast as boolean) ?? true,
        run_vigolium: (r.run_vigolium as boolean) ?? true,
        run_semgrep: (r.run_semgrep as boolean) ?? (asMapping(raw.leaks_and_secrets).run_semgrep as boolean) ?? true,
        run_react2shell: (asMapping(r.react_scanner).run_react2shell as boolean) ?? true,
        run_post_scan_processing: (r.run_post_scan_processing as boolean) ?? true,
        concurrency: (r.concurrency as number) ?? 50,
        rate_limit: (r.rate_limit as number) ?? 150,
        retries: (r.retries as number) ?? 1,
        timeout: (r.timeout as number) ?? 5,
        intensity: (r.intensity as 'normal' | 'aggressive' | 'light') ?? 'normal',
        fetch_gpt_report: (r.fetch_gpt_report as boolean) ?? true,
        enable_http_crawl: (r.enable_http_crawl as boolean) ?? true,
        wpscan_enumeration: (r.wpscan_enumeration as string) ?? 'vp,vt,u',
        wpscan_detection_mode: (r.wpscan_detection_mode as 'mixed' | 'passive' | 'aggressive') ?? 'mixed',
        acunetix: {
          submit_live_subdomains: ac.submit_live_subdomains ?? false,
          resubmit_after_days: typeof ac.resubmit_after_days === 'number' ? ac.resubmit_after_days : 3,
          start_scan_on_submit: ac.start_scan_on_submit ?? false,
        },
        nuclei: {
          use_nuclei_config: n.use_nuclei_config ?? false,
          severities: n.severities ?? ['unknown', 'info', 'low', 'medium', 'high', 'critical'],
          tags: n.tags ?? [],
          templates: n.templates ?? [],
          custom_templates: n.custom_templates ?? [],
        },
        cpanel_scanner: {
          run_cpanel2shell: cp.run_cpanel2shell ?? true,
          cpanel_user_wordlist: cp.cpanel_user_wordlist ?? '/usr/src/app/wordlist/cpanel_users.txt',
          proxy_type: cp.proxy_type ?? 'rotating',
        },
        vigolium: {
          strategy: vig.strategy ?? 'balanced',
          concurrency: vig.concurrency ?? 50,
          rate_limit: vig.rate_limit ?? 100,
          timeout: vig.timeout ?? '15s',
          run_phase_a: vig.run_phase_a ?? true,
          run_phase_b: vig.run_phase_b ?? true,
          scope_origin: (vig.scope_origin as 'all' | 'relaxed' | 'balanced' | 'strict') ?? 'balanced',
          skip_spidering: vig.skip_spidering ?? false,
        },
      };
    }, def.vulnerability_scan.config) as EngineConfig['vulnerability_scan'],

    attack_path_modeling: runFlagSection('attack_path_modeling', 'enabled', (r) => ({
      top_n: (r.top_n as number) ?? 5,
    })) as EngineConfig['attack_path_modeling'],

    tier_7: section('tier_7', (r) => ({
      high_noise_modules: (r.high_noise_modules as string[]) ?? def.tier_7.config.high_noise_modules,
    }), def.tier_7.config) as EngineConfig['tier_7'],

    vigolium_audit: runFlagSection('vigolium_audit', 'run_vigolium_audit', (r) => ({
      intensity: (r.intensity as 'quick' | 'balanced' | 'deep') ?? 'balanced',
      use_ai: (r.use_ai as boolean) ?? false,
      timeout: (r.timeout as number) ?? 3600,
    })) as EngineConfig['vigolium_audit'],
  };
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export interface UseEngineConfigReturn {
  config: EngineConfig;
  yaml: string;
  yamlError: string | null;
  updateSection: <K extends SectionKey>(
    section: K,
    patch: Partial<EngineConfig[K]['config']>
  ) => void;
  toggleSection: (section: SectionKey, enabled: boolean) => void;
  updateGlobal: (patch: Partial<GlobalConfig>) => void;
  setYaml: (raw: string) => void;
  loadTemplate: (yamlStr: string) => void;
}

export function useEngineConfig(initialYaml?: string): UseEngineConfigReturn {
  const [config, setConfig] = useState<EngineConfig>(() => {
    if (initialYaml) {
      try { return parseYamlToConfig(initialYaml); } catch { /* fall through */ }
    }
    return DEFAULT_ENGINE_CONFIG;
  });
  const [yaml, setYamlStr] = useState<string>(() => initialYaml ?? serialiseConfigToYaml(DEFAULT_ENGINE_CONFIG));
  const [yamlError, setYamlError] = useState<string | null>(null);
  // Keys of the loaded YAML the form does not own, re-emitted on every serialise.
  const leftovers = useRef<Leftovers>(NO_LEFTOVERS);

  const serialise = useCallback((next: EngineConfig) => serialiseConfigToYaml(next, leftovers.current), []);

  // Re-parse when initialYaml changes (edit mode load)
  useEffect(() => {
    if (!initialYaml) return;
    try {
      const parsed = parseYamlToConfig(initialYaml);
      leftovers.current = engineLeftovers(initialYaml);
      setConfig(parsed);
      setYamlStr(serialise(parsed));
      setYamlError(null);
    } catch (e) {
      setYamlError(e instanceof Error ? e.message : String(e));
    }
  }, [initialYaml, serialise]);

  // Keep yaml in sync when config changes
  const updateConfigAndYaml = useCallback((next: EngineConfig) => {
    setConfig(next);
    setYamlStr(serialise(next));
    setYamlError(null);
  }, [serialise]);

  const updateSection = useCallback(<K extends SectionKey>(
    section: K,
    patch: Partial<EngineConfig[K]['config']>
  ) => {
    setConfig((prev) => {
      const prevSection = prev[section];
      const next: EngineConfig = {
        ...prev,
        [section]: {
          ...prevSection,
          config: { ...prevSection.config, ...patch },
        },
      };
      setYamlStr(serialise(next));
      setYamlError(null);
      return next;
    });
  }, [serialise]);

  const toggleSection = useCallback((section: SectionKey, enabled: boolean) => {
    setConfig((prev) => {
      const next: EngineConfig = { ...prev, [section]: { ...prev[section], enabled } };
      setYamlStr(serialise(next));
      setYamlError(null);
      return next;
    });
  }, [serialise]);

  const updateGlobal = useCallback((patch: Partial<GlobalConfig>) => {
    setConfig((prev) => {
      const next: EngineConfig = { ...prev, global: { ...prev.global, ...patch } };
      setYamlStr(serialise(next));
      setYamlError(null);
      return next;
    });
  }, [serialise]);

  const setYaml = useCallback((raw: string) => {
    setYamlStr(raw);
    try {
      const parsed = parseYamlToConfig(raw);
      leftovers.current = engineLeftovers(raw);
      setConfig(parsed);
      setYamlError(null);
    } catch (e) {
      setYamlError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const loadTemplate = useCallback((yamlStr: string) => {
    try {
      const parsed = parseYamlToConfig(yamlStr);
      leftovers.current = engineLeftovers(yamlStr);
      updateConfigAndYaml(parsed);
    } catch (e) {
      setYamlError(e instanceof Error ? e.message : String(e));
    }
  }, [updateConfigAndYaml]);

  return { config, yaml, yamlError, updateSection, toggleSection, updateGlobal, setYaml, loadTemplate };
}

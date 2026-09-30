import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useEngineConfig } from '../useEngineConfig';

const ENGINE_YAML = `
threads: 12
osint:
  leaks_and_secrets:
    gitleaks: false
leaks_and_secrets:
  trufflehog: false
port_scan: true
vulnerability_scan:
  run_nuclei: false
  nuclei:
    tags: [cve]
  acunetix:
    resubmit_after_days: 7
`;

describe('useEngineConfig YAML parsing', () => {
  it('reads nested mappings and falls back to defaults for missing keys', () => {
    const { result } = renderHook(() => useEngineConfig(ENGINE_YAML));
    const { config } = result.current;

    expect(config.global.threads).toBe(12);
    expect(config.leaks_and_secrets).toEqual({
      enabled: true,
      config: { gitleaks: false, trufflehog: false, leaklookup: true },
    });
    expect(config.vulnerability_scan.config.run_nuclei).toBe(false);
    expect(config.vulnerability_scan.config.nuclei.tags).toEqual(['cve']);
    expect(config.vulnerability_scan.config.nuclei.templates).toEqual([]);
    expect(config.vulnerability_scan.config.acunetix?.resubmit_after_days).toBe(7);
    expect(config.vulnerability_scan.config.acunetix?.submit_live_subdomains).toBe(false);
  });

  it('treats a section given as a scalar as enabled with default settings', () => {
    const { result } = renderHook(() => useEngineConfig(ENGINE_YAML));
    expect(result.current.config.port_scan.enabled).toBe(true);
    expect(result.current.config.port_scan.config.ports).toEqual(['top-100']);
  });

  it('reports a YAML document that is not a mapping and keeps the last config', () => {
    const { result } = renderHook(() => useEngineConfig(ENGINE_YAML));
    act(() => result.current.setYaml('just a string'));

    expect(result.current.yamlError).toBe('Engine configuration must be a YAML mapping');
    expect(result.current.config.global.threads).toBe(12);
  });

  it('merges a section patch into that section only', () => {
    const { result } = renderHook(() => useEngineConfig(ENGINE_YAML));
    act(() => result.current.updateSection('port_scan', { rate_limit: 10 }));

    expect(result.current.config.port_scan.config.rate_limit).toBe(10);
    expect(result.current.config.port_scan.config.ports).toEqual(['top-100']);
    expect(result.current.yaml).toContain('rate_limit: 10');
  });
});

describe('useEngineConfig web_api_discovery checkboxes', () => {
  it('mirrors uses_tools when a run_<tool> flag is absent', () => {
    const yaml = `
web_api_discovery:
  uses_tools: [linkfinder, favirecon]
  run_julius: true
`;
    const { result } = renderHook(() => useEngineConfig(yaml));
    const { config } = result.current.config.web_api_discovery;

    expect(config.run_favirecon).toBe(true);
    expect(config.run_sourcemapper).toBe(false);
    expect(config.run_julius).toBe(true);
  });
});

describe('useEngineConfig secret scanning section', () => {
  it('reads secret_scanning so saving a built-in engine keeps it', () => {
    const yaml = `
secret_scanning:
  trufflehog: true
  gitleaks: false
  leaklookup: true
`;
    const { result } = renderHook(() => useEngineConfig(yaml));
    expect(result.current.config.leaks_and_secrets).toEqual({
      enabled: true,
      config: { gitleaks: false, trufflehog: true, leaklookup: true },
    });
  });

  it('writes the section as secret_scanning, including for older saves', () => {
    const { result } = renderHook(() => useEngineConfig('leaks_and_secrets:\n  leaklookup: false\n'));
    act(() => result.current.updateSection('leaks_and_secrets', { gitleaks: false }));

    expect(result.current.yaml).toMatch(/^secret_scanning:/m);
    expect(result.current.yaml).not.toMatch(/^leaks_and_secrets:/m);
    expect(result.current.yaml).toContain('leaklookup: false');
  });
});

describe('useEngineConfig email security section', () => {
  it('treats a missing section as enabled, like the backend', () => {
    const { result } = renderHook(() => useEngineConfig('port_scan: {}\n'));
    expect(result.current.config.email_security).toEqual({
      enabled: true,
      config: { mailbox_verification: true, timeout: 15, max_candidates: 200, delay_ms: 250, http_url: '' },
    });
  });

  it('reads the section switch and the mailbox verification settings', () => {
    const yaml = `
email_security:
  enabled: true
  mailbox_verification:
    enabled: false
    max_candidates: 50
    http_url: https://reacher.example.test
`;
    const { result } = renderHook(() => useEngineConfig(yaml));
    const { enabled, config } = result.current.config.email_security;

    expect(enabled).toBe(true);
    expect(config.mailbox_verification).toBe(false);
    expect(config.max_candidates).toBe(50);
    expect(config.timeout).toBe(15);
    expect(config.http_url).toBe('https://reacher.example.test');
  });

  it('writes an explicit enabled: false when the section is switched off', () => {
    const { result } = renderHook(() => useEngineConfig('port_scan: {}\n'));
    act(() => result.current.toggleSection('email_security', false));

    expect(result.current.yaml).toMatch(/^email_security:\n {2}enabled: false$/m);
  });

  it('keeps mailbox verification off after an edit mode reload', () => {
    const { result } = renderHook(() => useEngineConfig('port_scan: {}\n'));
    act(() => result.current.updateSection('email_security', { mailbox_verification: false }));
    const saved = result.current.yaml;

    const { result: reopened } = renderHook(() => useEngineConfig(saved));
    expect(reopened.current.config.email_security.enabled).toBe(true);
    expect(reopened.current.config.email_security.config.mailbox_verification).toBe(false);
    expect(reopened.current.yaml).not.toContain('http_url');
  });
});

describe('useEngineConfig keys the form does not own', () => {
  const HAND_EDITED = `
threads: 12
delay: 2
custom_section:
  answer: 42
port_scan:
  ports: [top-100]
`;

  it('keeps an unknown top-level key through an edit', () => {
    const { result } = renderHook(() => useEngineConfig(HAND_EDITED));
    act(() => result.current.updateGlobal({ threads: 20 }));

    expect(result.current.yaml).toMatch(/^threads: 20$/m);
    expect(result.current.yaml).toMatch(/^delay: 2$/m);
    expect(result.current.yaml).toMatch(/^custom_section:\n {2}answer: 42$/m);
  });

  it('does not bring back a section the user switched off', () => {
    const { result } = renderHook(() => useEngineConfig(HAND_EDITED));
    act(() => result.current.toggleSection('port_scan', false));

    expect(result.current.yaml).not.toMatch(/^port_scan:/m);
    expect(result.current.yaml).toMatch(/^custom_section:/m);
  });

  it('does not bring back a global reset to its default', () => {
    const { result } = renderHook(() => useEngineConfig('intensity: aggressive\n'));
    act(() => result.current.updateGlobal({ intensity: 'normal' }));

    expect(result.current.yaml).not.toMatch(/^intensity:/m);
  });

  it('takes unknown keys from YAML typed into the YAML tab', () => {
    const { result } = renderHook(() => useEngineConfig(HAND_EDITED));
    act(() => result.current.setYaml('other_section:\n  x: 1\n'));
    act(() => result.current.updateGlobal({ threads: 5 }));

    expect(result.current.yaml).toMatch(/^other_section:/m);
    expect(result.current.yaml).not.toMatch(/^custom_section:/m);
  });

  it('writes the Tier 7 correlation settings', () => {
    const { result } = renderHook(() => useEngineConfig('tier_7:\n  high_noise_modules: [a]\n'));
    act(() => result.current.updateSection('tier_7', { high_noise_modules: ['b'] }));

    expect(result.current.yaml).toMatch(/^tier_7:\n {2}high_noise_modules:\n {4}- b$/m);
  });
});

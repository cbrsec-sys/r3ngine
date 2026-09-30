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

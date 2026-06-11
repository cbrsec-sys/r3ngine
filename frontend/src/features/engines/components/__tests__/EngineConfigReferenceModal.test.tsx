/**
 * Tests for EngineConfigReferenceModal
 *
 * NOTE: This project does not currently have a frontend test runner installed
 * (no vitest, jest, or @testing-library/react in package.json).
 * These tests are written to the vitest + @testing-library/react standard
 * and will execute once those dependencies are added:
 *   npm install --save-dev vitest @testing-library/react @testing-library/jest-dom jsdom
 *
 * To enable, also add to vite.config.ts:
 *   test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'] }
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EngineConfigReferenceModal } from '../EngineConfigReferenceModal';
import * as api from '../../api';

vi.mock('../../api');

const MOCK_YAML = [
  'subdomain_discovery:',
  '  uses_tools:',
  '    - subfinder',
  '# A comment line',
  'port_scan:',
  '  timeout: 5',
].join('\n');

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  vi.mocked(api.useYamlConfigReference).mockReturnValue({
    data: MOCK_YAML,
    isLoading: false,
  } as any);
});

describe('EngineConfigReferenceModal', () => {
  it('renders modal title when open', () => {
    render(<EngineConfigReferenceModal open={true} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByText('CONFIGURATION REFERENCE')).toBeInTheDocument();
  });

  it('does not render content when closed', () => {
    render(<EngineConfigReferenceModal open={false} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.queryByText('CONFIGURATION REFERENCE')).not.toBeInTheDocument();
  });

  it('displays YAML lines from fetched content', () => {
    render(<EngineConfigReferenceModal open={true} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByText(/subdomain_discovery/)).toBeInTheDocument();
  });

  it('shows match indicator when search term found', () => {
    render(<EngineConfigReferenceModal open={true} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    fireEvent.change(screen.getByPlaceholderText('Search configuration keys...'), {
      target: { value: 'subfinder' },
    });
    expect(screen.getByText(/MATCH AT LINE/)).toBeInTheDocument();
  });

  it('shows NO MATCH when search term not present', () => {
    render(<EngineConfigReferenceModal open={true} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    fireEvent.change(screen.getByPlaceholderText('Search configuration keys...'), {
      target: { value: 'xyz_nonexistent_key' },
    });
    expect(screen.getByText('NO MATCH FOUND')).toBeInTheDocument();
  });

  it('shows line count when no search term', () => {
    render(<EngineConfigReferenceModal open={true} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByText(/6 LINES/)).toBeInTheDocument();
  });

  it('calls onClose when CLOSE button clicked', () => {
    const onClose = vi.fn();
    render(<EngineConfigReferenceModal open={true} onClose={onClose} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByText('CLOSE'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows loading spinner when isLoading is true', () => {
    vi.mocked(api.useYamlConfigReference).mockReturnValue({ data: undefined, isLoading: true } as any);
    render(<EngineConfigReferenceModal open={true} onClose={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});

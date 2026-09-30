import { fireEvent, render, screen } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { describe, expect, it, vi } from 'vitest';
import { hackerTheme } from '../../../../../theme';
import { DEFAULT_ENGINE_CONFIG } from '../../../types/engineConfig';
import { DirFileFuzzSection } from '../DirFileFuzzSection';

vi.mock('../../../../../theme/useThemeTokens', async () => {
  const { hackerTheme: theme } = await import('../../../../../theme');
  const { getResolvedTokens: resolve } = await import('../../../../../theme/tokens');
  return {
    useThemeTokens: () => ({ tokens: resolve('hacker'), theme, isLight: false, isCyber: true, themeName: 'hacker' }),
  };
});

const renderSection = (onChange = vi.fn()) => {
  render(
    <ThemeProvider theme={hackerTheme}>
      <DirFileFuzzSection
        config={{ ...DEFAULT_ENGINE_CONFIG.dir_file_fuzz.config, extensions: ['php'] }}
        enabled
        onToggle={vi.fn()}
        onChange={onChange}
      />
    </ThemeProvider>,
  );
  return onChange;
};

describe('DirFileFuzzSection', () => {
  it('shows ffuf as always on and dirsearch / feroxbuster as optional', () => {
    renderSection();

    expect(screen.getByText(/ffuf always fuzzes every target/)).toBeInTheDocument();
    const ffuf = screen.getByRole('checkbox', { name: 'ffuf (always runs)' });
    expect(ffuf).toBeChecked();
    expect(ffuf).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: 'dirsearch (extra pass)' })).toBeEnabled();
    expect(screen.getByRole('checkbox', { name: 'feroxbuster (extra pass)' })).toBeEnabled();
  });

  it('defaults to dirsearch and feroxbuster off', () => {
    const { run_dirsearch, run_feroxbuster, extensions } = DEFAULT_ENGINE_CONFIG.dir_file_fuzz.config;
    expect(run_dirsearch).toBe(false);
    expect(run_feroxbuster).toBe(false);
    expect(new Set(extensions).size).toBe(extensions.length);
  });

  it('ignores an extension that differs only by a dot or case', () => {
    const onChange = renderSection();
    const input = screen.getByRole('combobox', { name: 'Extensions' });
    fireEvent.change(input, { target: { value: '.PHP' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onChange).toHaveBeenLastCalledWith({ extensions: ['php'] });
  });
});

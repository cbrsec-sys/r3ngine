import { fireEvent, render, screen, within } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { describe, expect, it, vi } from 'vitest';
import { hackerTheme } from '../../../../theme';
import { DEFAULT_ENGINE_CONFIG } from '../../types/engineConfig';
import type { UseEngineConfigReturn } from '../../hooks/useEngineConfig';
import { EngineConfigTabs } from '../EngineConfigTabs';

vi.mock('../../../../theme/useThemeTokens', async () => {
  const { hackerTheme: theme } = await import('../../../../theme');
  const { getResolvedTokens: resolve } = await import('../../../../theme/tokens');
  return {
    useThemeTokens: () => ({ tokens: resolve('hacker'), theme, isLight: false, isCyber: true, themeName: 'hacker' }),
  };
});

const renderTabs = () => {
  const state: UseEngineConfigReturn = {
    config: DEFAULT_ENGINE_CONFIG,
    yaml: '',
    yamlError: null,
    updateSection: vi.fn(),
    toggleSection: vi.fn(),
    updateGlobal: vi.fn(),
    setYaml: vi.fn(),
    loadTemplate: vi.fn(),
  };
  render(
    <ThemeProvider theme={hackerTheme}>
      <EngineConfigTabs state={state} />
    </ThemeProvider>,
  );
  return state;
};

describe('EngineConfigTabs', () => {
  it('renders the finding grouping card between attack paths and the Vigolium audit on the Tier 7 tab', () => {
    renderTabs();
    fireEvent.click(screen.getByRole('tab', { name: 'Tier 7 — Intelligence' }));

    const panel = screen.getByRole('tabpanel');
    const titles = within(panel)
      .getAllByText(/^(Attack Path Modeling|Finding Grouping|Vigolium Audit)$/)
      .map((el) => el.textContent);
    expect(titles).toEqual(['Attack Path Modeling', 'Finding Grouping', 'Vigolium Audit']);
  });

  it('wires the finding grouping toggle to the tier_7 section', () => {
    const state = renderTabs();
    fireEvent.click(screen.getByRole('tab', { name: 'Tier 7 — Intelligence' }));

    const card = screen.getByText('Finding Grouping').closest('.MuiCard-root');
    expect(card).not.toBeNull();
    fireEvent.click(within(card as HTMLElement).getByRole('switch'));
    expect(state.toggleSection).toHaveBeenLastCalledWith('tier_7', false);
  });
});

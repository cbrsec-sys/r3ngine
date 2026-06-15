import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

/** Warn on new hardcoded color literals outside the theme layer */
const noHardcodedColors = {
  files: ['src/features/**/*.{ts,tsx}', 'src/components/**/*.{ts,tsx}'],
  ignores: ['src/theme/**'],
  rules: {
    'no-restricted-syntax': [
      'warn',
      {
        selector: 'Literal[value=/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]',
        message:
          'Avoid hardcoded hex colors in UI code. Use theme.palette, useThemeTokens(), or semanticColors helpers from src/theme/.',
      },
      {
        selector: 'Literal[value=/^rgba?\\(/]',
        message:
          'Avoid hardcoded rgba/rgb colors in UI code. Use theme.palette, useThemeTokens(), or semanticColors helpers from src/theme/.',
      },
    ],
  },
}

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  noHardcodedColors,
])

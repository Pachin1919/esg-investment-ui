import type { Config } from 'tailwindcss';

// Colors are CSS custom properties defined in src/index.css so light/dark swap in one place.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        page: 'var(--page)',
        surface: 'var(--surface-1)',
        ink: 'var(--text-primary)',
        ink2: 'var(--text-secondary)',
        muted: 'var(--text-muted)',
        grid: 'var(--grid)',
        line: 'var(--border)',
        accent: 'var(--series-1)',
      },
      fontFamily: { sans: ['system-ui', '-apple-system', 'Segoe UI', 'sans-serif'] },
    },
  },
  plugins: [],
} satisfies Config;

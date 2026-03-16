import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:      '#09090f',
        surface: '#111120',
        card:    '#18182e',
        border:  '#25254a',
        accent:  '#c084fc',
        t1:      '#e2e8f4',
        t2:      '#b8c5d6',
        t3:      '#859ab5',
        success: '#4ade80',
        warn:    '#fbbf24',
        danger:  '#f87171',
        info:    '#38bdf8',
      },
    },
  },
  plugins: [],
} satisfies Config

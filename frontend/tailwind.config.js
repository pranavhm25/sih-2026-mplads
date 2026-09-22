/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Source Sans 3"', 'system-ui', 'sans-serif'],
        plex: ['"IBM Plex Sans"', '"Source Sans 3"', 'sans-serif'],
        serif: ['"IBM Plex Serif"', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        canvas: '#f5f2ec',
        paper: '#fdfcf9',
        ink: {
          DEFAULT: '#1e222a',
          soft: '#4a5261',
          faint: '#7d8694',
        },
        rule: '#d8d3c8',
        accent: {
          DEFAULT: '#2d4a8a',
          soft: '#eef1f8',
        },
        vermilion: '#b3402a',
        amber: {
          signal: '#a86a12',
          soft: '#faf3e3',
        },
        forest: '#2e6b45',
        verms: {
          soft: '#f9ebe7',
        },
        forestsoft: '#e9f2ec',
      },
      fontSize: {
        meta: ['11px', '14px'],
      },
    },
  },
  plugins: [],
}

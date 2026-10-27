/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0f131c',
        'surface-lowest': '#0a0e16',
        'surface-low': '#181c24',
        'surface-base': '#1c2028',
        'surface-high': '#262a33',
        'surface-bright': '#31353e',
        'on-surface': '#dfe2ee',
        'on-surface-variant': '#c2c6d6',
        outline: '#8c909f',
        // Severity Palette
        'severity-micro': '#4edea3',
        'severity-minor': '#adc6ff',
        'severity-moderate': '#ffb690',
        'severity-strong': '#ec6a06',
        'severity-critical': '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}

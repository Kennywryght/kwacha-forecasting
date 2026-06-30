export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1e3a5f",
        accent:  "#2563eb",
        // New design system colors
        gold: {
          300: '#E0AC4F',
          400: '#C9963E',
          500: '#B08030',
        },
        terracotta: {
          400: '#D2693C',
          500: '#B8552E',
        },
        ink: {
          950: '#0B0F0D',
        },
        stone: {
          100: '#EAEDE9',
          300: '#D2D8D2',
          400: '#A3ACA3',
          500: '#7A857A',
          600: '#5C6B62',
          700: '#3D4A41',
          900: '#1A211D',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        data: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
    }
  },
  plugins: []
}
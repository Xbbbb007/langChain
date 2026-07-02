/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae2fd',
          300: '#7cc8fc',
          400: '#38abfa',
          500: '#0e90e9',
          600: '#0272c7',
          700: '#035ba1',
          800: '#074e85',
          900: '#0c426e',
          950: '#082a4a',
        }
      }
    },
  },
  plugins: [],
}

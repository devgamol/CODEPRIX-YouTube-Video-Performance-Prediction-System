/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#060b18',
        'dark-2': '#0f1420',
      },
      backgroundColor: {
        'dark': '#060b18',
      },
      opacity: {
        '5': '0.05',
        '10': '0.1',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'background-primary': 'var(--color-background-primary)',
        'background-secondary': 'var(--color-background-secondary)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'accent': 'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        'border-color': 'var(--color-border)',
      }
    },
  },
  plugins: [
    require('tailwind-scrollbar'),
  ],
}


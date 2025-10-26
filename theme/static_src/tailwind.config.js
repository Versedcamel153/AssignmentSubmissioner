/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../../templates/**/*.html',
    '../../../**/templates/**/*.html',
  ],
  theme: {
    extend: {
       fontFamily: {
        sans: ['Nunito', 'sans-serif'], // This makes Nunito the default for font-sans
      },
    },
  },
  plugins: [
    require('daisyui'),
    require("tailgrids/plugin")
  ],
}

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1117",
        surface: "#171b26",
        border: "#2a3144",
        accent: "#6c8cff",
        accent2: "#4fd1c5",
      },
    },
  },
  plugins: [],
};

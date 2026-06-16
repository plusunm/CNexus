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
        coreGoal: "#2F6BFF",
        reflection: "#8A5CFF",
        stableMemory: "#2ED47A",
        pending: "#FFCC00",
        conflict: "#FF4D4F",
        cognitiveBg: "#0B0F1A",
        cognitivePanel: "#1A1F2C",
      },
    },
  },
  plugins: [],
};

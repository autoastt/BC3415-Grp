/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F1F3EF",
        ink: "#1D2B2F",
        muted: "#5B6969",
        line: "#D3D9D1",
        teal: { DEFAULT: "#0F5C6B", dark: "#0A4552", soft: "#DDEAEA" },
        mustard: { DEFAULT: "#E0A526", soft: "#F8EDCF", deep: "#8A6210" },
        brick: { DEFAULT: "#B3412E", soft: "#F6E1DC" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Public Sans"', "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

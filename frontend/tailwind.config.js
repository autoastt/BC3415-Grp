/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Shared with the sample company site (frontend/public/sample-site.html);
      // the two are meant to read as one brand, so change both together.
      colors: {
        // Warm neutrals, matching the sample site's --paper/--ink/--muted/--line.
        paper: "#F7F3EC",
        ink: "#231A16",
        muted: "#6B5F58",
        line: "#E4DCD1",
        // Brand/primary, matching the sample site's --flame.
        flame: { DEFAULT: "#B3412E", dark: "#8E3020", soft: "#F6E1DC" },
        // Success and handoff, matching the sample site's --ok.
        teal: { DEFAULT: "#0F5C6B", dark: "#0A4552", soft: "#DDEAEA" },
        mustard: { DEFAULT: "#E0A526", soft: "#F8EDCF", deep: "#8A6210" },
        // Errors and destructive actions. Deliberately darker than flame: with a
        // red brand colour, a filled Delete must not look like a filled primary.
        brick: { DEFAULT: "#7F1D1D", soft: "#F4DAD6" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Public Sans"', "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

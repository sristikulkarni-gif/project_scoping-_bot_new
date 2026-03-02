/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#7c3aed",
        secondary: "#06b6d4",
        accent: "#8b5cf6",
        background: "#0a0d1a",
        surface: "#0f1324",
        dark: {
          primary: "#7c3aed",
          secondary: "#06b6d4",
          accent: "#8b5cf6",
          muted: "#1a2035",
          background: "#0a0d1a",
          surface: "#0f1324",
        },
      },
      fontFamily: {
        sans: ["'Inter'", "system-ui", "sans-serif"],
        heading: ["'Inter'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 4px 24px rgba(0,0,0,0.4), 0 1px 4px rgba(0,0,0,0.3)",
        glow: "0 0 24px rgba(139,92,246,0.25), 0 4px 16px rgba(0,0,0,0.5)",
        "glow-lg": "0 0 40px rgba(139,92,246,0.35), 0 8px 32px rgba(0,0,0,0.6)",
        dark: "0 4px 24px rgba(0,0,0,0.6)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.25rem",
        "3xl": "1.75rem",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      backdropBlur: { xs: "2px" },
      transitionDuration: { "400": "400ms" },
    },
  },
  plugins: [],
};

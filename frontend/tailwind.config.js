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
        //  Light mode palette
        primary: "var(--primary)",
        secondary: "var(--secondary)",
        accent: "var(--accent)",
        muted: "var(--muted)", // Ensure this variable exists or keep a fallback
        background: "var(--light)",
        surface: "#ffffff",   // White

        // Dark mode palette
        dark: {
          primary: "#6366f1", // Update these too or map to vars
          secondary: "#ec4899",
          accent: "#8b5cf6",
          muted: "#94a3b8",
          background: "var(--dark)",
          surface: "#1e293b",
        },
      },
      fontFamily: {
        sans: ["'Nunito Sans'", "system-ui", "sans-serif"],
        heading: ["'Poppins'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 4px 10px rgba(0,0,0,0.05)",
        glow: "0 0 20px rgba(13, 148, 136, 0.3), 0 4px 12px rgba(0, 0, 0, 0.1)",
        "glow-lg": "0 0 30px rgba(13, 148, 136, 0.4), 0 8px 20px rgba(0, 0, 0, 0.15)",
        dark: "0 4px 15px rgba(0,0,0,0.4)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'slide-in': 'slideIn 0.5s ease-out forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(-20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'shimmer': 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '112': '28rem',
        '128': '32rem',
      },
      transitionDuration: {
        '400': '400ms',
        '600': '600ms',
      },
      backdropBlur: {
        xs: '2px',
      },
      letterSpacing: {
        tightest: '-.075em',
        wider: '.05em',
      },
    },
  },
  plugins: [],
};


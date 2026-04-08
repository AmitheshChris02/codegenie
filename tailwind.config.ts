import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef9f9",
          100: "#d4efef",
          200: "#acdfdf",
          300: "#7fcaca",
          400: "#4cb0b0",
          500: "#319696",
          600: "#25797b",
          700: "#226265",
          800: "#214f52",
          900: "#203f42"
        }
      },
      boxShadow: {
        soft: "0 8px 30px rgba(2, 12, 27, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;


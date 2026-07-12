import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          700: "#0F766E"
        },
        chapel: {
          gold: "#B38B2E",
          ink: "#123330",
          mist: "#E8F3F1"
        }
      },
      boxShadow: {
        calm: "0 18px 50px rgba(15, 118, 110, 0.12)"
      }
    }
  },
  plugins: []
};

export default config;


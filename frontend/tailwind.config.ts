import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16130f",
        paper: "#faf7f2",
        brand: { DEFAULT: "#1f6f50", dark: "#165039", light: "#e3f1ea" },
        accent: "#d9822b",
      },
      fontFamily: { sans: ["var(--font-sans)", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        base: "#017587",
        surface: "#E9EDF6",
        "text-primary": "#1F242A",
        "text-secondary": "#5B6064",
        accent: "#F0B419",
        danger: "#8B4343",
        cream: "#F5F5F0",
        navy: "#1F242A",
        maroon: "#8B4343",
        "status-green": "#2ECC71",
        "status-red": "#E74C3C",
      },
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        sans: ["Plus Jakarta Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.25,1,0.5,1)",
      },
    },
  },
  plugins: [],
};

export default config;

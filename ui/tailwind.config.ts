import type { Config } from "tailwindcss";

/**
 * Tokens lifted directly from /DESIGN.md.
 * Treat any drift between the two as a design bug, not a code bug.
 */
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#0A0A0A",
          surface: "#18181B",
          elevated: "#27272A",
          light: "#FAFAF9",
          "light-surface": "#FFFFFF",
          "light-elevated": "#F4F4F3",
        },
        ink: {
          primary: "#FAFAF9",
          secondary: "#D4D4D8",
          muted: "#71717A",
        },
        line: {
          DEFAULT: "#27272A",
          strong: "#3F3F46",
        },
        improved: {
          DEFAULT: "#10F09C",
          soft: "rgba(16, 240, 156, 0.10)",
          ring: "rgba(16, 240, 156, 0.35)",
        },
        clear: {
          correctness: "#60A5FA",
          latency: "#A78BFA",
          execution: "#FBBF24",
          adherence: "#34D399",
          relevance: "#F472B6",
          safety: "#F87171",
          cost: "#FB923C",
        },
        state: {
          success: "#10B981",
          warn: "#F59E0B",
          error: "#EF4444",
          info: "#3B82F6",
        },
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular"],
        code: ["var(--font-jetbrains-mono)", "ui-monospace", "SFMono-Regular"],
      },
      fontSize: {
        "display-xl": ["64px", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "display-lg": ["48px", { lineHeight: "1.1",  letterSpacing: "-0.02em" }],
        "display-md": ["32px", { lineHeight: "1.15", letterSpacing: "-0.015em" }],
        "title":      ["24px", { lineHeight: "1.25" }],
        "body-lg":    ["18px", { lineHeight: "1.5"  }],
        "body":       ["16px", { lineHeight: "1.5"  }],
        "ui":         ["14px", { lineHeight: "1.4"  }],
        "ui-sm":      ["12px", { lineHeight: "1.4"  }],
      },
      borderRadius: {
        xs: "2px",
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
      },
      spacing: {
        "5xl": "96px",
      },
      transitionTimingFunction: {
        "ease-hero": "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "ease-out-soft": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      transitionDuration: {
        instant: "50ms",
        micro: "150ms",
        short: "300ms",
        hero: "400ms",
      },
      backgroundImage: {
        "hairline-grid":
          "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
      },
      keyframes: {
        "pareto-sweep": {
          "0%":   { strokeDashoffset: "var(--pareto-len, 1000)", opacity: "0" },
          "20%":  { opacity: "1" },
          "100%": { strokeDashoffset: "0", opacity: "1" },
        },
        "ring-pulse": {
          "0%":   { transform: "scale(1)",   opacity: "0.85" },
          "100%": { transform: "scale(2.4)", opacity: "0"    },
        },
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)"   },
        },
      },
      animation: {
        "pareto-sweep": "pareto-sweep 400ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards",
        "ring-pulse":   "ring-pulse 200ms ease-out forwards",
        "fade-up":      "fade-up 300ms cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
};

export default config;

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0A0E1A',
          secondary: '#111827',
          card: '#111827',
          elevated: '#1C2537',
        },
        border: {
          DEFAULT: '#1F2937',
          accent: '#2D3748',
        },
        accent: {
          green: '#00FF87',
          'green-dim': '#00CC6A',
          'green-dark': '#004D29',
          blue: '#3B82F6',
          'blue-dim': '#2563EB',
        },
        danger: '#EF4444',
        warning: '#F59E0B',
        text: {
          primary: '#F9FAFB',
          secondary: '#9CA3AF',
          muted: '#6B7280',
        },
      },
      fontFamily: {
        heading: ['Rajdhani', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      animation: {
        'fill-bar': 'fillBar 0.8s ease-out forwards',
        'pulse-green': 'pulseGreen 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        fillBar: {
          '0%': { width: '0%' },
          '100%': { width: 'var(--bar-width)' },
        },
        pulseGreen: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0, 255, 135, 0.4)' },
          '50%': { boxShadow: '0 0 20px 8px rgba(0, 255, 135, 0.2)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%, 100%': { filter: 'drop-shadow(0 0 4px rgba(0, 255, 135, 0.3))' },
          '50%': { filter: 'drop-shadow(0 0 12px rgba(0, 255, 135, 0.7))' },
        },
      },
      backgroundImage: {
        'grid-pattern': "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
        'pitch-green': 'linear-gradient(160deg, #1a4d2e 0%, #0f3320 50%, #1a4d2e 100%)',
      },
      backgroundSize: {
        'grid-sm': '20px 20px',
      },
    },
  },
  plugins: [],
}

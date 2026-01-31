/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          bg: '#FAFAFA',
          surface: '#FFFFFF',
          border: '#E5E5E5',
          text: '#1D1D1F',
          secondary: '#86868B',
          accent: '#0071E3',
          critical: '#FF3B30',
          warning: '#FF9500',
          success: '#34C759',
          info: '#007AFF',
          ai: {
            start: '#5856D6',
            end: '#AF52DE'
          }
        }
      },
      fontFamily: {
        display: ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        body: ['Inter', 'SF Pro Text', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'monospace']
      },
      fontSize: {
        'hero': ['72px', { lineHeight: '1', fontWeight: '300' }],
        'title': ['28px', { lineHeight: '1.2', fontWeight: '600' }],
        'section': ['17px', { lineHeight: '1.4', fontWeight: '600' }],
        'body': ['15px', { lineHeight: '1.6', fontWeight: '400' }],
        'caption': ['13px', { lineHeight: '1.4', fontWeight: '400' }],
        'data': ['14px', { lineHeight: '1.4', fontWeight: '400' }]
      },
      animation: {
        'pulse-slow': 'pulse-slow 2s ease-in-out infinite',
        'glow': 'glow 3s ease-in-out infinite',
        'fade-in': 'fade-in 200ms ease-out',
        'slide-up': 'slide-up 400ms cubic-bezier(0.32, 0.72, 0, 1)',
        'expand': 'expand 350ms cubic-bezier(0.4, 0, 0.2, 1)'
      },
      keyframes: {
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.85' }
        },
        'glow': {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' }
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        'slide-up': {
          '0%': { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(0)' }
        },
        'expand': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        }
      },
      boxShadow: {
        'apple': '0 4px 20px rgba(0, 0, 0, 0.08)',
        'apple-lg': '0 8px 40px rgba(0, 0, 0, 0.12)',
        'apple-glow': '0 0 20px rgba(88, 86, 214, 0.3)'
      }
    },
  },
  plugins: [],
}

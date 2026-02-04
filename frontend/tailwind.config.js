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
          bg: '#F5F5F7',
          surface: '#FFFFFF',
          elevated: '#FBFBFD',
          border: '#D2D2D7',
          divider: '#E8E8ED',
          text: '#1D1D1F',
          secondary: '#6E6E73',
          tertiary: '#86868B',
          muted: '#AEAEB2',
          accent: '#0071E3',
          critical: '#FF3B30',
          warning: '#FF9500',
          success: '#30D158',
          info: '#007AFF',
          ai: {
            start: '#5856D6',
            end: '#AF52DE'
          },
          grey: {
            50: '#FAFAFA',
            100: '#F5F5F7',
            200: '#E8E8ED',
            300: '#D2D2D7',
            400: '#AEAEB2',
            500: '#8E8E93',
            600: '#636366',
            700: '#48484A',
            800: '#3A3A3C',
            900: '#1D1D1F'
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
        'apple': '0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.04)',
        'apple-sm': '0 1px 2px rgba(0, 0, 0, 0.03), 0 2px 6px rgba(0, 0, 0, 0.03)',
        'apple-md': '0 2px 8px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.06)',
        'apple-lg': '0 4px 16px rgba(0, 0, 0, 0.08), 0 16px 48px rgba(0, 0, 0, 0.08)',
        'apple-inset': 'inset 0 1px 2px rgba(0, 0, 0, 0.04)',
        'apple-glow': '0 0 20px rgba(88, 86, 214, 0.3)',
        'apple-ring': '0 0 0 4px rgba(0, 113, 227, 0.15)'
      },
      borderRadius: {
        'apple-sm': '8px',
        'apple': '12px',
        'apple-lg': '16px',
        'apple-xl': '20px',
        'apple-2xl': '24px'
      }
    },
  },
  plugins: [],
}

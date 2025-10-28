import typography from '@tailwindcss/typography';
import containerQuries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				base: {
					50: 'var(--color-base-50, #f8fafc)',
					100: 'var(--color-base-100, #ffffff)',
					200: 'var(--color-base-200, #e2e8f0)',
					300: 'var(--color-base-300, #cbd5f5)',
					400: 'var(--color-base-400, #94a3b8)',
					500: 'var(--color-base-500, #64748b)',
					600: 'var(--color-base-600, #475569)',
					700: 'var(--color-base-700, #334155)',
					800: 'var(--color-base-800, #1f2937)',
					900: 'var(--color-base-900, #111827)',
					950: 'var(--color-base-950, #0b1120)'
				},
				primary: {
					50: 'var(--color-primary-50, #eff6ff)',
					100: 'var(--color-primary-100, #dbeafe)',
					200: 'var(--color-primary-200, #bfdbfe)',
					300: 'var(--color-primary-300, #93c5fd)',
					400: 'var(--color-primary-400, #60a5fa)',
					500: 'var(--color-primary-500, #3b82f6)',
					600: 'var(--color-primary-600, #2563eb)',
					700: 'var(--color-primary-700, #1d4ed8)',
					800: 'var(--color-primary-800, #1e40af)',
					900: 'var(--color-primary-900, #1e3a8a)',
					950: 'var(--color-primary-950, #172554)'
				},
				success: {
					50: 'var(--color-success-50, #ecfdf5)',
					100: 'var(--color-success-100, #d1fae5)',
					200: 'var(--color-success-200, #a7f3d0)',
					300: 'var(--color-success-300, #6ee7b7)',
					400: 'var(--color-success-400, #34d399)',
					500: 'var(--color-success-500, #10b981)',
					600: 'var(--color-success-600, #059669)',
					700: 'var(--color-success-700, #047857)',
					800: 'var(--color-success-800, #065f46)',
					900: 'var(--color-success-900, #064e3b)',
					950: 'var(--color-success-950, #022c22)'
				},
				error: {
					50: 'var(--color-error-50, #fef2f2)',
					100: 'var(--color-error-100, #fee2e2)',
					200: 'var(--color-error-200, #fecaca)',
					300: 'var(--color-error-300, #fca5a5)',
					400: 'var(--color-error-400, #f87171)',
					500: 'var(--color-error-500, #ef4444)',
					600: 'var(--color-error-600, #dc2626)',
					700: 'var(--color-error-700, #b91c1c)',
					800: 'var(--color-error-800, #991b1b)',
					900: 'var(--color-error-900, #7f1d1d)',
					950: 'var(--color-error-950, #450a0a)'
				},
				gray: {
					50: 'var(--color-gray-50, #f9f9f9)',
					100: 'var(--color-gray-100, #ececec)',
					200: 'var(--color-gray-200, #e3e3e3)',
					300: 'var(--color-gray-300, #cdcdcd)',
					400: 'var(--color-gray-400, #b4b4b4)',
					500: 'var(--color-gray-500, #9b9b9b)',
					600: 'var(--color-gray-600, #676767)',
					700: 'var(--color-gray-700, #4e4e4e)',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			}
		}
	},
	plugins: [typography, containerQuries]
};

/**
 * Design tokens lifted from /design_guidelines.json so the app reads as the
 * same product as the web frontend. Brutalist streetwear: near-black surfaces,
 * silver secondary, neon green accent, square corners, 1px technical borders.
 *
 * Keep this in sync with design_guidelines.json — it is the source of truth.
 */
export const colors = {
  background: '#050505',
  surface: '#0F0F0F',
  surfaceRaised: '#1A1A1A',
  primary: '#39FF14',
  primaryPressed: '#32E012',
  primaryText: '#000000',
  secondary: '#C0C0C0',
  textMain: '#F3F4F6',
  textMuted: '#9CA3AF',
  border: '#27272A',
  borderLight: 'rgba(255, 255, 255, 0.1)',
  danger: '#F87171',
  warning: '#FBBF24',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

/**
 * The web app uses Clash Display / Satoshi. Rather than ship font binaries we
 * lean on the platform faces and carry the *character* across with weight,
 * tracking and uppercase treatment — which is what actually makes the brand
 * legible at a glance.
 */
export const type = {
  h1: {
    fontSize: 34,
    fontWeight: '900' as const,
    letterSpacing: -1,
    textTransform: 'uppercase' as const,
    color: colors.textMain,
  },
  h2: {
    fontSize: 24,
    fontWeight: '800' as const,
    letterSpacing: -0.5,
    textTransform: 'uppercase' as const,
    color: colors.textMain,
  },
  h3: {
    fontSize: 18,
    fontWeight: '700' as const,
    letterSpacing: -0.2,
    color: colors.textMain,
  },
  body: {
    fontSize: 15,
    fontWeight: '400' as const,
    lineHeight: 22,
    color: colors.textMuted,
  },
  bodyStrong: {
    fontSize: 15,
    fontWeight: '600' as const,
    color: colors.textMain,
  },
  overline: {
    fontSize: 11,
    fontWeight: '700' as const,
    letterSpacing: 2,
    textTransform: 'uppercase' as const,
    color: colors.secondary,
  },
  mono: {
    fontSize: 15,
    fontVariant: ['tabular-nums'] as const,
    color: colors.textMain,
  },
} as const;

/** Square corners everywhere — the design language has no rounded surfaces. */
export const radius = 0;

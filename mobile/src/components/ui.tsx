import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, type } from '../theme';

/**
 * The shared kit. Square corners, 1px borders, uppercase headings — the
 * "technical grid" look from design_guidelines.json. Screens should not
 * hand-roll these; if something is missing, add it here.
 */

export function Screen({
  children,
  scroll = false,
  refreshControl,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  refreshControl?: React.ReactElement;
}) {
  if (scroll) {
    return (
      <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          refreshControl={refreshControl}
        >
          {children}
        </ScrollView>
      </SafeAreaView>
    );
  }
  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      {children}
    </SafeAreaView>
  );
}

export function Heading({ children, level = 1 }: { children: React.ReactNode; level?: 1 | 2 | 3 }) {
  const style = level === 1 ? type.h1 : level === 2 ? type.h2 : type.h3;
  return <Text style={[style, styles.headingSpacing]}>{children}</Text>;
}

export function Overline({ children }: { children: React.ReactNode }) {
  return <Text style={type.overline}>{children}</Text>;
}

export function Body({
  children,
  muted = true,
}: {
  children: React.ReactNode;
  muted?: boolean;
}) {
  return <Text style={muted ? type.body : type.bodyStrong}>{children}</Text>;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  loading?: boolean;
  disabled?: boolean;
}) {
  const isDisabled = disabled || loading;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.button,
        variant === 'primary' && styles.buttonPrimary,
        variant === 'secondary' && styles.buttonSecondary,
        variant === 'danger' && styles.buttonDanger,
        pressed && !isDisabled && styles.buttonPressed,
        isDisabled && styles.buttonDisabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? colors.primaryText : colors.textMain} />
      ) : (
        <Text
          style={[
            styles.buttonLabel,
            variant === 'primary' ? styles.buttonLabelPrimary : styles.buttonLabelOnDark,
            variant === 'danger' && styles.buttonLabelDanger,
          ]}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}

interface FieldProps extends TextInputProps {
  label: string;
  /** Field-level error, shown under the input in danger red. */
  error?: string | null;
  hint?: string;
}

export function Field({ label, error, hint, style, ...inputProps }: FieldProps) {
  return (
    <View style={styles.field}>
      <Text style={[type.overline, styles.fieldLabel]}>{label}</Text>
      <TextInput
        placeholderTextColor="#4B5563"
        {...inputProps}
        style={[styles.input, !!error && styles.inputError, style]}
      />
      {!!hint && !error && <Text style={styles.hint}>{hint}</Text>}
      {!!error && <Text style={styles.fieldError}>{error}</Text>}
    </View>
  );
}

export function Badge({
  children,
  tone = 'accent',
}: {
  children: React.ReactNode;
  tone?: 'accent' | 'muted' | 'warning';
}) {
  return (
    <View
      style={[
        styles.badge,
        tone === 'muted' && styles.badgeMuted,
        tone === 'warning' && styles.badgeWarning,
      ]}
    >
      <Text
        style={[
          styles.badgeText,
          tone === 'muted' && styles.badgeTextMuted,
          tone === 'warning' && styles.badgeTextWarning,
        ]}
      >
        {children}
      </Text>
    </View>
  );
}

/** Full-width inline error with an optional retry — used for failed loads. */
export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={styles.errorNotice}>
      <Text style={styles.errorNoticeText}>{message}</Text>
      {!!onRetry && (
        <Pressable onPress={onRetry} accessibilityRole="button">
          <Text style={styles.errorNoticeRetry}>TAP TO RETRY</Text>
        </Pressable>
      )}
    </View>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: { label: string; onPress: () => void };
}) {
  return (
    <View style={styles.empty}>
      <Text style={[type.h3, styles.emptyTitle]}>{title}</Text>
      <Text style={[type.body, styles.emptyMessage]}>{message}</Text>
      {!!action && (
        <View style={styles.emptyAction}>
          <Button label={action.label} onPress={action.onPress} variant="secondary" />
        </View>
      )}
    </View>
  );
}

export function Loading({ label }: { label?: string }) {
  return (
    <View style={styles.loading}>
      <ActivityIndicator color={colors.primary} size="large" />
      {!!label && <Text style={styles.loadingLabel}>{label}</Text>}
    </View>
  );
}

/** Hairline rule matching the web app's border-collapse sections. */
export function Divider() {
  return <View style={styles.divider} />;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  scrollContent: { padding: spacing.lg, paddingBottom: spacing.xxl },
  headingSpacing: { marginBottom: spacing.md },

  button: {
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    borderWidth: 1,
  },
  buttonPrimary: { backgroundColor: colors.primary, borderColor: colors.primary },
  buttonSecondary: { backgroundColor: 'transparent', borderColor: colors.borderLight },
  buttonDanger: { backgroundColor: 'transparent', borderColor: colors.danger },
  buttonPressed: { opacity: 0.75 },
  buttonDisabled: { opacity: 0.4 },
  buttonLabel: { fontSize: 14, fontWeight: '800', letterSpacing: 1.5, textTransform: 'uppercase' },
  buttonLabelPrimary: { color: colors.primaryText },
  buttonLabelOnDark: { color: colors.textMain },
  buttonLabelDanger: { color: colors.danger },

  field: { marginBottom: spacing.md },
  fieldLabel: { marginBottom: spacing.sm },
  input: {
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: 'transparent',
    color: colors.textMain,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    fontSize: 16,
  },
  inputError: { borderColor: colors.danger },
  hint: { color: colors.textMuted, fontSize: 12, marginTop: spacing.xs },
  fieldError: { color: colors.danger, fontSize: 13, marginTop: spacing.xs },

  badge: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.3)',
    backgroundColor: 'rgba(57, 255, 20, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeMuted: { borderColor: colors.borderLight, backgroundColor: 'transparent' },
  badgeWarning: {
    borderColor: 'rgba(251, 191, 36, 0.35)',
    backgroundColor: 'rgba(251, 191, 36, 0.1)',
  },
  badgeText: {
    color: colors.primary,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  badgeTextMuted: { color: colors.textMuted },
  badgeTextWarning: { color: colors.warning },

  errorNotice: {
    borderWidth: 1,
    borderColor: 'rgba(248, 113, 113, 0.4)',
    backgroundColor: 'rgba(248, 113, 113, 0.08)',
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  errorNoticeText: { color: colors.danger, fontSize: 14, lineHeight: 20 },
  errorNoticeRetry: {
    color: colors.danger,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
    marginTop: spacing.sm,
  },

  empty: { paddingVertical: spacing.xxl, alignItems: 'center' },
  emptyTitle: { marginBottom: spacing.sm, textAlign: 'center' },
  emptyMessage: { textAlign: 'center', maxWidth: 300 },
  emptyAction: { marginTop: spacing.lg, alignSelf: 'stretch' },

  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl },
  loadingLabel: { ...type.body, marginTop: spacing.md },

  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.lg },
});

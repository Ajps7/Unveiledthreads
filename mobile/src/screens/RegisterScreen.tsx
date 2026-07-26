import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ApiError, NetworkError } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { AuthStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Body, Button, ErrorNotice, Field, Heading, Screen } from '../components/ui';

type Props = NativeStackScreenProps<AuthStackParamList, 'Register'>;

/**
 * Mirrors the backend password policy (validate_password in backend/core.py):
 * minimum 8 characters, no composition rules, common passwords rejected
 * server-side. This check is a courtesy so the user gets instant feedback —
 * the server remains authoritative and will reject anything this misses.
 */
const MIN_PASSWORD_LENGTH = 8;

export function RegisterScreen({ navigation }: Props) {
  const { signUp } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const passwordProblem =
    password.length > 0 && password.length < MIN_PASSWORD_LENGTH
      ? `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
      : null;
  const confirmProblem =
    confirm.length > 0 && confirm !== password ? 'Passwords do not match.' : null;

  const canSubmit =
    name.trim().length > 0 &&
    email.trim().length > 0 &&
    password.length >= MIN_PASSWORD_LENGTH &&
    confirm === password &&
    acceptedTerms;

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await signUp(email, password, name);
    } catch (err) {
      if (err instanceof NetworkError) {
        setError(err.message);
      } else if (err instanceof ApiError) {
        // Surface the server's specific copy — it distinguishes "email already
        // exists", "password too common" and "password too long" for us.
        setError(
          err.isRateLimited
            ? 'Too many sign-up attempts from this network. Try again shortly.'
            : err.detail,
        );
      } else {
        setError('Something went wrong. Try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen scroll>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <Text style={styles.wordmark}>UNVEILED THREADS</Text>
          <Heading level={1}>Create account</Heading>
          <Body>Buy from vetted independent UK brands, with Buyer Protection on every order.</Body>
        </View>

        {!!error && <ErrorNotice message={error} />}

        <Field
          label="Name"
          value={name}
          onChangeText={setName}
          autoComplete="name"
          textContentType="name"
          placeholder="Your name"
          editable={!submitting}
        />

        <Field
          label="Email"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          placeholder="you@example.com"
          editable={!submitting}
        />

        <Field
          label="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize="none"
          autoComplete="new-password"
          textContentType="newPassword"
          placeholder="At least 8 characters"
          hint="Three random words beat a short complicated one."
          error={passwordProblem}
          editable={!submitting}
        />

        <Field
          label="Confirm password"
          value={confirm}
          onChangeText={setConfirm}
          secureTextEntry
          autoCapitalize="none"
          placeholder="Repeat your password"
          error={confirmProblem}
          editable={!submitting}
        />

        <Pressable
          onPress={() => setAcceptedTerms((value) => !value)}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: acceptedTerms }}
          style={styles.termsRow}
        >
          <View style={[styles.checkbox, acceptedTerms && styles.checkboxChecked]}>
            {acceptedTerms && <Text style={styles.checkboxMark}>✓</Text>}
          </View>
          <Text style={styles.termsText}>
            I accept the Terms &amp; Conditions and the Privacy Policy.
          </Text>
        </Pressable>

        <View style={styles.actions}>
          <Button
            label="Create account"
            onPress={handleSubmit}
            loading={submitting}
            disabled={!canSubmit}
          />
        </View>

        <View style={styles.footer}>
          <Text style={type.body}>Already have an account? </Text>
          <Pressable onPress={() => navigation.navigate('Login')} accessibilityRole="button">
            <Text style={styles.link}>Sign in</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { marginBottom: spacing.xl },
  wordmark: { ...type.overline, color: colors.primary, marginBottom: spacing.lg },
  actions: { marginTop: spacing.md },
  termsRow: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.sm },
  checkbox: {
    width: 22,
    height: 22,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  checkboxChecked: { borderColor: colors.primary, backgroundColor: colors.primary },
  checkboxMark: { color: colors.primaryText, fontSize: 14, fontWeight: '900' },
  termsText: { ...type.body, flex: 1, fontSize: 13 },
  footer: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  link: { color: colors.primary, fontSize: 14, fontWeight: '600' },
});

import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ApiError, NetworkError } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { AuthStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Body, Button, ErrorNotice, Field, Heading, Screen } from '../components/ui';

type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;

export function LoginScreen({ navigation }: Props) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = email.trim().length > 0 && password.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await signIn(email, password);
      // No navigation call — RootNavigator swaps the stack once status flips.
    } catch (err) {
      if (err instanceof NetworkError) {
        setError(err.message);
      } else if (err instanceof ApiError) {
        // The backend returns a deliberately generic message on bad
        // credentials to avoid confirming which emails exist. Pass it through
        // verbatim rather than inventing something more specific.
        setError(
          err.isRateLimited
            ? 'Too many attempts. Wait a minute and try again.'
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
          <Heading level={1}>Sign in</Heading>
          <Body>UK streetwear from independent brands.</Body>
        </View>

        {!!error && <ErrorNotice message={error} />}

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
          autoComplete="current-password"
          textContentType="password"
          placeholder="••••••••"
          editable={!submitting}
          onSubmitEditing={handleSubmit}
          returnKeyType="go"
        />

        <View style={styles.actions}>
          <Button
            label="Sign in"
            onPress={handleSubmit}
            loading={submitting}
            disabled={!canSubmit}
          />
        </View>

        <Pressable
          onPress={() => navigation.navigate('ForgotPassword')}
          accessibilityRole="button"
          style={styles.linkRow}
        >
          <Text style={styles.link}>Forgot password?</Text>
        </Pressable>

        <View style={styles.footer}>
          <Text style={type.body}>No account yet? </Text>
          <Pressable onPress={() => navigation.navigate('Register')} accessibilityRole="button">
            <Text style={styles.link}>Create one</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { marginBottom: spacing.xl },
  wordmark: { ...type.overline, color: colors.primary, marginBottom: spacing.lg },
  actions: { marginTop: spacing.sm },
  linkRow: { marginTop: spacing.lg, alignItems: 'center' },
  link: { color: colors.primary, fontSize: 14, fontWeight: '600' },
  footer: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

import React, { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ApiError, NetworkError } from '../api/client';
import { auth } from '../api/endpoints';
import type { AccountStackParamList } from '../navigation/types';
import { spacing } from '../theme';
import { Body, Button, ErrorNotice, Field, Heading, Screen } from '../components/ui';

type Props = NativeStackScreenProps<AccountStackParamList, 'ChangePassword'>;

/** Matches validate_password() in backend/core.py — see RegisterScreen. */
const MIN_PASSWORD_LENGTH = 8;

export function ChangePasswordScreen({ navigation }: Props) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const lengthProblem =
    next.length > 0 && next.length < MIN_PASSWORD_LENGTH
      ? `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
      : null;
  const sameProblem =
    next.length > 0 && next === current ? 'New password must be different from your current one.' : null;
  const confirmProblem = confirm.length > 0 && confirm !== next ? 'Passwords do not match.' : null;

  const canSubmit =
    current.length > 0 &&
    next.length >= MIN_PASSWORD_LENGTH &&
    next !== current &&
    confirm === next;

  const handleSubmit = async () => {
    if (!canSubmit || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await auth.changePassword(current, next);
      Alert.alert('Password updated', 'Use your new password next time you sign in.', [
        { text: 'Done', onPress: () => navigation.goBack() },
      ]);
    } catch (err) {
      if (err instanceof NetworkError) {
        setError(err.message);
      } else if (err instanceof ApiError) {
        // 401 here means the current password was wrong — not an expired
        // session — so show it inline instead of bouncing to sign-in.
        setError(
          err.isRateLimited
            ? 'Too many attempts. Try again in an hour.'
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
        <Heading level={2}>Change password</Heading>
        <Body>
          Pick something you do not use anywhere else. Length beats complexity — three random words
          is stronger than one short word with symbols.
        </Body>

        <View style={styles.form}>
          {!!error && <ErrorNotice message={error} />}

          <Field
            label="Current password"
            value={current}
            onChangeText={setCurrent}
            secureTextEntry
            autoCapitalize="none"
            autoComplete="current-password"
            editable={!submitting}
          />

          <Field
            label="New password"
            value={next}
            onChangeText={setNext}
            secureTextEntry
            autoCapitalize="none"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            error={lengthProblem ?? sameProblem}
            editable={!submitting}
          />

          <Field
            label="Confirm new password"
            value={confirm}
            onChangeText={setConfirm}
            secureTextEntry
            autoCapitalize="none"
            error={confirmProblem}
            editable={!submitting}
          />

          <Button
            label="Update password"
            onPress={handleSubmit}
            loading={submitting}
            disabled={!canSubmit}
          />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  form: { marginTop: spacing.xl, gap: spacing.xs },
});

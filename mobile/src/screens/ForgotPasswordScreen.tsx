import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ApiError, NetworkError } from '../api/client';
import { auth } from '../api/endpoints';
import type { AuthStackParamList } from '../navigation/types';
import { spacing } from '../theme';
import { Body, Button, ErrorNotice, Field, Heading, Screen } from '../components/ui';

type Props = NativeStackScreenProps<AuthStackParamList, 'ForgotPassword'>;

export function ForgotPasswordScreen({ navigation }: Props) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!email.trim() || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await auth.forgotPassword(email.trim().toLowerCase());
      // The endpoint always returns the same generic response whether or not
      // the account exists, so that an attacker cannot enumerate emails. We
      // show the same confirmation for the same reason.
      setSent(true);
    } catch (err) {
      if (err instanceof NetworkError) setError(err.message);
      else if (err instanceof ApiError)
        setError(
          err.isRateLimited
            ? 'Too many reset requests. Try again in an hour.'
            : err.detail,
        );
      else setError('Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <Screen scroll>
        <Heading level={1}>Check your email</Heading>
        <Body>
          If an account exists for {email.trim().toLowerCase()}, we have sent a reset link. It
          expires in one hour. The link opens in your browser.
        </Body>
        <View style={styles.actions}>
          <Button
            label="Back to sign in"
            variant="secondary"
            onPress={() => navigation.navigate('Login')}
          />
        </View>
      </Screen>
    );
  }

  return (
    <Screen scroll>
      <Heading level={1}>Reset password</Heading>
      <Body>Enter your email and we will send you a link to set a new password.</Body>

      <View style={styles.form}>
        {!!error && <ErrorNotice message={error} />}
        <Field
          label="Email"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          placeholder="you@example.com"
          editable={!submitting}
          onSubmitEditing={handleSubmit}
          returnKeyType="send"
        />
        <Button
          label="Send reset link"
          onPress={handleSubmit}
          loading={submitting}
          disabled={!email.trim()}
        />
      </View>

      <View style={styles.actions}>
        <Button label="Back" variant="secondary" onPress={() => navigation.goBack()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  form: { marginTop: spacing.xl },
  actions: { marginTop: spacing.lg },
});

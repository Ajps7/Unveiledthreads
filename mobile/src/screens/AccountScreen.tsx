import React, { useState } from 'react';
import { Alert, Linking, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { WEB_BASE_URL } from '../api/config';
import { account } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { messageFromError } from '../hooks/useAsyncData';
import type { AccountStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Body, Button, Divider, ErrorNotice, Heading, Screen } from '../components/ui';

type Props = NativeStackScreenProps<AccountStackParamList, 'Account'>;

export function AccountScreen({ navigation }: Props) {
  const { user, signOut } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  /**
   * UK GDPR Article 20. The endpoint returns the full JSON dump. A mobile
   * screen is a poor place to render that, so we confirm it was produced and
   * point the user at the web account page to download it properly.
   */
  const handleExport = async () => {
    setError(null);
    setExporting(true);
    try {
      const data = await account.export();
      const sections = Object.keys(data).length;
      Alert.alert(
        'Your data is ready',
        `We assembled ${sections} section${sections === 1 ? '' : 's'} of your data. ` +
          'Open your account page on the web to download the full file.',
        [
          { text: 'Not now', style: 'cancel' },
          {
            text: 'Open website',
            onPress: () => void Linking.openURL(`${WEB_BASE_URL}/account`),
          },
        ],
      );
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setExporting(false);
    }
  };

  /**
   * Article 17 erasure is irreversible and cascades across orders, messages
   * and reviews. It needs a password plus a typed confirmation, which is a
   * deliberate friction we are not going to reimplement as a mobile prompt —
   * we send the user to the web flow that already does it correctly.
   */
  const handleDelete = () => {
    Alert.alert(
      'Delete your account',
      'This permanently deletes your account and cannot be undone. For your safety this is ' +
        'completed on the website, where we can verify your password properly.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Open website',
          style: 'destructive',
          onPress: () => void Linking.openURL(`${WEB_BASE_URL}/account`),
        },
      ],
    );
  };

  const handleSignOut = () => {
    Alert.alert('Sign out', 'You will need to sign in again to buy or message brands.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign out', style: 'destructive', onPress: () => void signOut() },
    ]);
  };

  return (
    <Screen scroll>
      <Heading level={1}>Account</Heading>

      <View style={styles.identity}>
        <Text style={styles.name}>{user?.name ?? '—'}</Text>
        <Text style={styles.email}>{user?.email ?? ''}</Text>
        {user?.role === 'brand' && (
          <Text style={styles.roleNote}>
            You sell on Unveiled Threads. Listings, orders to fulfil and payouts are managed on the
            website.
          </Text>
        )}
      </View>

      {!!error && <ErrorNotice message={error} />}

      <Divider />

      <Text style={type.overline}>Activity</Text>
      <View style={styles.group}>
        <Button
          label="My orders"
          variant="secondary"
          onPress={() => navigation.navigate('Orders')}
        />
        <Button
          label="Notifications"
          variant="secondary"
          onPress={() => navigation.navigate('Notifications')}
        />
      </View>

      <Divider />

      <Text style={type.overline}>Security</Text>
      <View style={styles.group}>
        <Button
          label="Change password"
          variant="secondary"
          onPress={() => navigation.navigate('ChangePassword')}
        />
      </View>

      <Divider />

      <Text style={type.overline}>Your data</Text>
      <View style={styles.group}>
        <Body>
          You can export everything we hold about you, or delete your account entirely. Both are
          your rights under UK GDPR.
        </Body>
        <View style={styles.stack}>
          <Button
            label="Export my data"
            variant="secondary"
            onPress={handleExport}
            loading={exporting}
          />
          <Button label="Delete my account" variant="danger" onPress={handleDelete} />
        </View>
      </View>

      <Divider />

      <View style={styles.group}>
        <Button label="Sign out" variant="secondary" onPress={handleSignOut} />
      </View>

      <View style={styles.legal}>
        <Text style={styles.legalText}>
          Selling, brand applications and disputes live on the website.
        </Text>
        <Text
          style={styles.legalLink}
          onPress={() => void Linking.openURL(`${WEB_BASE_URL}/terms`)}
        >
          Terms &amp; Conditions
        </Text>
        <Text
          style={styles.legalLink}
          onPress={() => void Linking.openURL(`${WEB_BASE_URL}/privacy`)}
        >
          Privacy Policy
        </Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  identity: { marginBottom: spacing.md },
  name: { color: colors.textMain, fontSize: 20, fontWeight: '800' },
  email: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  roleNote: { color: colors.primary, fontSize: 12, lineHeight: 18, marginTop: spacing.sm },
  group: { marginTop: spacing.md, gap: spacing.md },
  stack: { gap: spacing.sm },
  legal: { marginTop: spacing.xl, gap: spacing.sm },
  legalText: { color: colors.textMuted, fontSize: 12, lineHeight: 18 },
  legalLink: { color: colors.primary, fontSize: 13, fontWeight: '600' },
});

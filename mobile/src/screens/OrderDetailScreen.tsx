import React from 'react';
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { orders as ordersApi } from '../api/endpoints';
import type { Order } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import { getTrackingUrl } from '../lib/courierTracking';
import { gbp, shortDate, shippingLabel } from '../lib/format';
import type { OrdersStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Badge, Button, Divider, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<OrdersStackParamList, 'OrderDetail'>;

/** The Vinted-style timeline the web app shows, in order. */
const TIMELINE: { key: string; label: string }[] = [
  { key: 'confirmed', label: 'Order confirmed' },
  { key: 'processing', label: 'Being packed' },
  { key: 'shipped', label: 'Shipped' },
  { key: 'in_transit', label: 'In transit' },
  { key: 'out_for_delivery', label: 'Out for delivery' },
  { key: 'delivered', label: 'Delivered' },
];

export function OrderDetailScreen({ route }: Props) {
  const { orderId } = route.params;

  // There is no GET /orders/{id}, so read the list and pick this one out.
  // The list is capped at 50 and sorted newest-first, which covers the case
  // a user reaches this screen from the orders list.
  const state = useAsyncData<Order | null>(
    async (signal) => {
      const all = await ordersApi.mine(signal);
      return all.find((candidate) => candidate.id === orderId) ?? null;
    },
    [orderId],
  );

  if (state.loading && !state.data) return <Loading />;

  if (state.error && !state.data) {
    return (
      <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
        <View style={styles.padded}>
          <ErrorNotice message={state.error} onRetry={state.reload} />
        </View>
      </SafeAreaView>
    );
  }

  const order = state.data;
  if (!order) {
    return (
      <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
        <View style={styles.padded}>
          <Text style={type.h3}>Order not found</Text>
          <Text style={type.body}>
            We could not find that order on your account. Pull back and refresh your orders.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  const currentStatus = order.shipping_status ?? 'confirmed';
  const currentIndex = TIMELINE.findIndex((step) => step.key === currentStatus);
  const trackingUrl = getTrackingUrl(order.courier, order.tracking_number);
  const credit = order.credit_applied ?? 0;

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={type.overline}>{order.brand_name}</Text>
        <Text style={[type.h2, styles.title]}>{order.product_name}</Text>
        <Text style={styles.meta}>
          Size {order.size} · Ordered {shortDate(order.created_at)}
        </Text>

        <View style={styles.badgeRow}>
          <Badge tone={currentStatus === 'delivered' ? 'accent' : 'muted'}>
            {shippingLabel(currentStatus)}
          </Badge>
        </View>

        <Divider />

        <Text style={type.overline}>Progress</Text>
        <View style={styles.timeline}>
          {TIMELINE.map((step, index) => {
            const reached = currentIndex >= 0 && index <= currentIndex;
            return (
              <View key={step.key} style={styles.timelineRow}>
                <View style={[styles.dot, reached && styles.dotReached]} />
                <Text style={[styles.timelineLabel, reached && styles.timelineLabelReached]}>
                  {step.label}
                </Text>
              </View>
            );
          })}
        </View>

        {!!order.tracking_number && (
          <>
            <Divider />
            <Text style={type.overline}>Tracking</Text>
            <Text style={styles.tracking}>{order.tracking_number}</Text>
            {!!order.courier && <Text style={styles.meta}>via {order.courier}</Text>}
            {trackingUrl ? (
              <View style={styles.trackButton}>
                <Button
                  label={`Track on ${order.courier}`}
                  onPress={() => void Linking.openURL(trackingUrl)}
                  variant="secondary"
                />
              </View>
            ) : (
              <Text style={styles.trackNote}>
                We do not have a tracking link for this courier — use the number above on their
                website.
              </Text>
            )}
          </>
        )}

        <Divider />

        <Text style={type.overline}>Receipt</Text>
        <View style={styles.receipt}>
          <Row label="Item" value={gbp(order.price)} />
          <Row label="Buyer Protection" value={gbp(order.platform_fee)} />
          {credit > 0 && <Row label="Referral credit" value={`−${gbp(credit)}`} accent />}
          <Row
            label="Shipping"
            value={order.shipping_cost > 0 ? gbp(order.shipping_cost) : 'Free'}
          />
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Total paid</Text>
            <Text style={styles.totalValue}>{gbp(order.total_charged)}</Text>
          </View>
        </View>

        <Text style={styles.footnote}>
          {order.brand_name} posts this parcel themselves. Any problem with the order is covered by
          Buyer Protection — start a dispute from the website if it does not arrive as described.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, accent && styles.rowValueAccent]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  padded: { padding: spacing.lg },
  title: { marginTop: spacing.xs },
  meta: { color: colors.textMuted, fontSize: 13, marginTop: spacing.xs },
  badgeRow: { flexDirection: 'row', marginTop: spacing.md },

  timeline: { marginTop: spacing.md, gap: spacing.md },
  timelineRow: { flexDirection: 'row', alignItems: 'center' },
  dot: {
    width: 10,
    height: 10,
    borderWidth: 1,
    borderColor: colors.border,
    marginRight: spacing.md,
  },
  dotReached: { backgroundColor: colors.primary, borderColor: colors.primary },
  timelineLabel: { color: colors.textMuted, fontSize: 14 },
  timelineLabelReached: { color: colors.textMain, fontWeight: '600' },

  tracking: {
    color: colors.textMain,
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
  trackButton: { marginTop: spacing.md },
  trackNote: { color: colors.textMuted, fontSize: 12, lineHeight: 18, marginTop: spacing.sm },

  receipt: { marginTop: spacing.md, borderWidth: 1, borderColor: colors.borderLight },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
  },
  rowLabel: { color: colors.textMuted, fontSize: 14 },
  rowValue: { color: colors.textMain, fontSize: 14, fontWeight: '600' },
  rowValueAccent: { color: colors.primary },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  totalLabel: { ...type.overline, color: colors.textMain },
  totalValue: { color: colors.primary, fontSize: 18, fontWeight: '900' },
  footnote: { color: colors.textMuted, fontSize: 12, lineHeight: 18, marginTop: spacing.lg },
});

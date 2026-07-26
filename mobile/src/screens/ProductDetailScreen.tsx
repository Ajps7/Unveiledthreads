import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { resolveImageUrl } from '../api/config';
import { products as productsApi, wishlist as wishlistApi } from '../api/endpoints';
import type { Product } from '../api/types';
import { useAsyncData, messageFromError } from '../hooks/useAsyncData';
import { useCheckout } from '../hooks/useCheckout';
import { BUYER_PROTECTION_BLURB, buildBreakdown } from '../lib/fees';
import { gbp } from '../lib/format';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { MainTabParamList, ShopStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Badge, Body, Button, Divider, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<ShopStackParamList, 'ProductDetail'>;

export function ProductDetailScreen({ route, navigation }: Props) {
  const { productId } = route.params;
  const { width } = useWindowDimensions();

  const product = useAsyncData<Product>((signal) => productsApi.get(productId, signal), [productId]);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [wishlisted, setWishlisted] = useState(false);
  const [wishlistBusy, setWishlistBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const checkout = useCheckout();

  // View tracking is analytics only — never block or fail the screen on it.
  useEffect(() => {
    void productsApi.trackView(productId);
  }, [productId]);

  useEffect(() => {
    let cancelled = false;
    wishlistApi
      .ids()
      .then((ids) => {
        if (!cancelled) setWishlisted(ids.includes(productId));
      })
      .catch(() => {
        // Signed-out or offline: leave the heart in its default state rather
        // than showing an error for something this peripheral.
      });
    return () => {
      cancelled = true;
    };
  }, [productId]);

  // Auto-select when there is only one size — one less tap before buying.
  useEffect(() => {
    const sizes = product.data?.sizes;
    if (sizes?.length === 1) setSelectedSize(sizes[0]);
  }, [product.data?.sizes]);

  const toggleWishlist = useCallback(async () => {
    if (wishlistBusy) return;
    setWishlistBusy(true);
    const next = !wishlisted;
    setWishlisted(next); // optimistic
    try {
      if (next) await wishlistApi.add(productId);
      else await wishlistApi.remove(productId);
    } catch (error) {
      setWishlisted(!next); // roll back
      setActionError(messageFromError(error));
    } finally {
      setWishlistBusy(false);
    }
  }, [productId, wishlisted, wishlistBusy]);

  const handleBuy = useCallback(async () => {
    const item = product.data;
    if (!item || !selectedSize) return;
    setActionError(null);

    const outcome = await checkout.start(item.id, selectedSize);

    switch (outcome.kind) {
      case 'paid':
        Alert.alert(
          'Order confirmed',
          `${item.brand_name} has been notified and will post your parcel. You will get an email receipt and tracking as soon as it ships.`,
          [
            {
              text: 'View my orders',
              onPress: () =>
                navigation
                  .getParent<BottomTabNavigationProp<MainTabParamList>>()
                  ?.navigate('OrdersTab', { screen: 'Orders' }),
            },
          ],
        );
        product.reload(); // stock has moved
        break;
      case 'not_paid':
        setActionError(
          'We have not seen payment for that order yet. If you completed checkout it may take a moment — check My Orders shortly.',
        );
        break;
      case 'error':
        setActionError(outcome.message);
        break;
      case 'cancelled':
      default:
        break;
    }
  }, [product, selectedSize, checkout, navigation]);

  if (product.loading && !product.data) return <Loading label="Loading piece" />;

  if (product.error && !product.data) {
    return (
      <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
        <View style={styles.errorWrap}>
          <ErrorNotice message={product.error} onRetry={product.reload} />
          <Button label="Back to shop" variant="secondary" onPress={() => navigation.goBack()} />
        </View>
      </SafeAreaView>
    );
  }

  const item = product.data;
  if (!item) return null;

  const soldOut = item.stock <= 0;
  const cannotSell = item.seller_payments_ready === false;
  const breakdown = buildBreakdown(item.price, item.shipping_cost ?? 0);
  const image = resolveImageUrl(item.images?.[0]);
  const buyDisabled = soldOut || cannotSell || !selectedSize || checkout.busy;

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={[styles.hero, { height: width }]}>
          {image ? (
            <Image source={{ uri: image }} style={styles.heroImage} resizeMode="cover" />
          ) : (
            <View style={[styles.heroImage, styles.heroFallback]}>
              <Text style={type.overline}>No image</Text>
            </View>
          )}
        </View>

        <View style={styles.body}>
          <Text style={type.overline}>{item.brand_name}</Text>
          <Text style={[type.h2, styles.name]}>{item.name}</Text>
          <Text style={styles.price}>{gbp(item.price)}</Text>

          <View style={styles.badges}>
            {soldOut && <Badge tone="muted">Sold out</Badge>}
            {!soldOut && item.stock <= 5 && <Badge>Only {item.stock} left</Badge>}
            {!!item.condition && <Badge tone="muted">{item.condition.replace(/_/g, ' ')}</Badge>}
            {!!item.is_dead_stock && <Badge tone="warning">Dead stock</Badge>}
          </View>

          {cannotSell && (
            <View style={styles.notice}>
              <Text style={styles.noticeText}>
                {item.brand_name} is still completing payment setup, so this piece cannot be bought
                just yet. Add it to your wishlist and we will keep it handy.
              </Text>
            </View>
          )}

          {!!actionError && <ErrorNotice message={actionError} />}

          <Divider />

          <Text style={type.overline}>Select size</Text>
          <View style={styles.sizeRow}>
            {(item.sizes ?? []).map((size) => (
              <Pressable
                key={size}
                onPress={() => setSelectedSize(size)}
                accessibilityRole="button"
                accessibilityState={{ selected: selectedSize === size }}
                style={[styles.size, selectedSize === size && styles.sizeActive]}
              >
                <Text
                  style={[styles.sizeLabel, selectedSize === size && styles.sizeLabelActive]}
                >
                  {size}
                </Text>
              </Pressable>
            ))}
          </View>

          <Divider />

          <Text style={type.overline}>What you pay</Text>
          <View style={styles.breakdown}>
            <Row label="Item" value={gbp(breakdown.item)} />
            <Row label="Buyer Protection" value={gbp(breakdown.buyerProtection)} />
            <Row
              label="Shipping"
              value={breakdown.shipping > 0 ? gbp(breakdown.shipping) : 'Free'}
            />
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Total</Text>
              <Text style={styles.totalValue}>{gbp(breakdown.total)}</Text>
            </View>
          </View>
          <Text style={styles.feeNote}>{BUYER_PROTECTION_BLURB}</Text>

          {!!item.description && (
            <>
              <Divider />
              <Text style={type.overline}>Details</Text>
              <View style={styles.description}>
                <Body>{item.description}</Body>
              </View>
              <View style={styles.specs}>
                {!!item.colour && <Spec label="Colour" value={item.colour} />}
                {!!item.material && <Spec label="Material" value={item.material} />}
                {!!item.fit && <Spec label="Fit" value={item.fit} />}
                {!!item.gender && <Spec label="Fit for" value={item.gender} />}
              </View>
            </>
          )}
        </View>
      </ScrollView>

      <View style={styles.actionBar}>
        <Pressable
          onPress={toggleWishlist}
          disabled={wishlistBusy}
          accessibilityRole="button"
          accessibilityLabel={wishlisted ? 'Remove from wishlist' : 'Save to wishlist'}
          style={styles.wishlistButton}
        >
          <Text style={[styles.wishlistIcon, wishlisted && styles.wishlistIconActive]}>
            {wishlisted ? '♥' : '♡'}
          </Text>
        </Pressable>
        <View style={styles.buyButton}>
          <Button
            label={
              soldOut
                ? 'Sold out'
                : cannotSell
                  ? 'Unavailable'
                  : selectedSize
                    ? `Buy — ${gbp(breakdown.total)}`
                    : 'Select a size'
            }
            onPress={handleBuy}
            loading={checkout.busy}
            disabled={buyDisabled}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.spec}>
      <Text style={styles.specLabel}>{label}</Text>
      <Text style={styles.specValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { paddingBottom: spacing.xxl },
  errorWrap: { padding: spacing.lg },
  hero: { width: '100%', backgroundColor: colors.surface },
  heroImage: { width: '100%', height: '100%' },
  heroFallback: { alignItems: 'center', justifyContent: 'center' },
  body: { padding: spacing.lg },
  name: { marginTop: spacing.sm },
  price: { color: colors.primary, fontSize: 26, fontWeight: '900', marginTop: spacing.xs },
  badges: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },

  notice: {
    borderWidth: 1,
    borderColor: 'rgba(251, 191, 36, 0.35)',
    backgroundColor: 'rgba(251, 191, 36, 0.08)',
    padding: spacing.md,
    marginTop: spacing.md,
  },
  noticeText: { color: colors.warning, fontSize: 13, lineHeight: 19 },

  sizeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },
  size: {
    minWidth: 56,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
  },
  sizeActive: { borderColor: colors.primary, backgroundColor: 'rgba(57, 255, 20, 0.1)' },
  sizeLabel: { color: colors.textMuted, fontWeight: '700', fontSize: 13 },
  sizeLabelActive: { color: colors.primary },

  breakdown: { marginTop: spacing.md, borderWidth: 1, borderColor: colors.borderLight },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
  },
  rowLabel: { color: colors.textMuted, fontSize: 14 },
  rowValue: { color: colors.textMain, fontSize: 14, fontWeight: '600' },
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
  feeNote: { color: colors.textMuted, fontSize: 12, lineHeight: 18, marginTop: spacing.sm },

  description: { marginTop: spacing.sm },
  specs: { marginTop: spacing.md, gap: spacing.sm },
  spec: { flexDirection: 'row', justifyContent: 'space-between' },
  specLabel: { ...type.overline, fontSize: 10 },
  specValue: { color: colors.textMain, fontSize: 13, textTransform: 'capitalize' },

  actionBar: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.background,
  },
  wishlistButton: {
    width: 56,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  wishlistIcon: { fontSize: 22, color: colors.textMuted },
  wishlistIconActive: { color: colors.primary },
  buyButton: { flex: 1 },
});

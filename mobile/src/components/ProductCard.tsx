import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { resolveImageUrl } from '../api/config';
import type { Product } from '../api/types';
import { gbp } from '../lib/format';
import { colors, spacing, type } from '../theme';
import { Badge } from './ui';

/**
 * Grid cell for the shop. Deliberately flat and bordered rather than a raised
 * card — the web product grid uses border-collapse, and rounded shadowed cards
 * would read as a different product.
 */
export function ProductCard({
  product,
  onPress,
  width,
}: {
  product: Product;
  onPress: (product: Product) => void;
  width: number;
}) {
  const image = resolveImageUrl(product.images?.[0]);
  const soldOut = product.stock <= 0;
  // A brand that has not finished Stripe onboarding cannot take money, so
  // checkout will reject this item. Say so here rather than at the last step.
  const cannotSell = product.seller_payments_ready === false;

  return (
    <Pressable
      onPress={() => onPress(product)}
      accessibilityRole="button"
      accessibilityLabel={`${product.name} by ${product.brand_name}, ${gbp(product.price)}`}
      style={({ pressed }) => [styles.card, { width }, pressed && styles.pressed]}
    >
      <View style={styles.imageWrap}>
        {image ? (
          <Image source={{ uri: image }} style={styles.image} resizeMode="cover" />
        ) : (
          <View style={[styles.image, styles.imageFallback]}>
            <Text style={styles.imageFallbackText}>NO IMAGE</Text>
          </View>
        )}
        {soldOut && (
          <View style={styles.overlay}>
            <Badge tone="muted">Sold out</Badge>
          </View>
        )}
        {!soldOut && cannotSell && (
          <View style={styles.overlay}>
            <Badge tone="warning">Not yet selling</Badge>
          </View>
        )}
      </View>

      <View style={styles.meta}>
        <Text style={styles.brand} numberOfLines={1}>
          {product.brand_name}
        </Text>
        <Text style={styles.name} numberOfLines={2}>
          {product.name}
        </Text>
        <Text style={styles.price}>{gbp(product.price)}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderColor: colors.borderLight, marginBottom: spacing.md },
  pressed: { borderColor: colors.primary, opacity: 0.9 },
  imageWrap: { aspectRatio: 1, backgroundColor: colors.surface },
  image: { width: '100%', height: '100%' },
  imageFallback: { alignItems: 'center', justifyContent: 'center' },
  imageFallbackText: { ...type.overline, color: colors.border },
  overlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(5, 5, 5, 0.7)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  meta: { padding: spacing.sm, gap: 2 },
  brand: { ...type.overline, fontSize: 10 },
  name: { color: colors.textMain, fontSize: 13, fontWeight: '600', lineHeight: 17 },
  price: { color: colors.primary, fontSize: 14, fontWeight: '800', marginTop: 2 },
});

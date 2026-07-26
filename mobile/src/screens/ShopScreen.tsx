import React, { useCallback, useMemo, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { products as productsApi } from '../api/endpoints';
import type { Product, ProductFilters } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import type { ShopStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { ProductCard } from '../components/ProductCard';
import { EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<ShopStackParamList, 'Shop'>;

type SortKey = NonNullable<ProductFilters['sort']>;

const SORTS: { key: SortKey; label: string }[] = [
  { key: 'latest', label: 'Latest' },
  { key: 'price_low', label: 'Price ↑' },
  { key: 'price_high', label: 'Price ↓' },
];

const GRID_GAP = spacing.md;
const HORIZONTAL_PADDING = spacing.lg;

export function ShopScreen({ navigation }: Props) {
  const { width } = useWindowDimensions();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>('latest');

  // Typing should not fire a request per keystroke; the backend regex search
  // is not cheap and /api/products has no dedicated rate limit of its own.
  const debouncedSearch = useDebouncedValue(search, 350);

  const categories = useAsyncData<string[]>((signal) => productsApi.categories(signal), []);

  const feed = useAsyncData<Product[]>(
    (signal) =>
      productsApi.list(
        {
          search: debouncedSearch.trim() || undefined,
          category: category ?? undefined,
          sort,
          limit: 50,
        },
        signal,
      ),
    [debouncedSearch, category, sort],
  );

  // Two columns, with the gap accounted for so cards never overflow the row.
  const cardWidth = useMemo(
    () => Math.floor((width - HORIZONTAL_PADDING * 2 - GRID_GAP) / 2),
    [width],
  );

  const openProduct = useCallback(
    (product: Product) =>
      navigation.navigate('ProductDetail', {
        productId: product.id,
        productName: product.name,
      }),
    [navigation],
  );

  const listItems = feed.data ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={styles.wordmark}>UNVEILED THREADS</Text>
        <Text style={type.h1}>Shop</Text>
      </View>

      <View style={styles.searchWrap}>
        <TextInput
          value={search}
          onChangeText={setSearch}
          placeholder="Search brands, pieces, materials"
          placeholderTextColor="#4B5563"
          style={styles.search}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType="search"
          accessibilityLabel="Search products"
        />
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipRow}
      >
        <Chip label="All" active={category === null} onPress={() => setCategory(null)} />
        {(categories.data ?? []).map((item) => (
          <Chip
            key={item}
            label={item}
            active={category === item}
            onPress={() => setCategory(category === item ? null : item)}
          />
        ))}
      </ScrollView>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipRow}
      >
        {SORTS.map((option) => (
          <Chip
            key={option.key}
            label={option.label}
            active={sort === option.key}
            onPress={() => setSort(option.key)}
          />
        ))}
      </ScrollView>

      {feed.loading && !feed.data ? (
        <Loading label="Loading the rail" />
      ) : (
        <FlatList
          data={listItems}
          keyExtractor={(item) => item.id}
          numColumns={2}
          columnWrapperStyle={styles.column}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={feed.refreshing}
              onRefresh={feed.refresh}
              tintColor={colors.primary}
            />
          }
          ListHeaderComponent={
            feed.error ? <ErrorNotice message={feed.error} onRetry={feed.reload} /> : null
          }
          ListEmptyComponent={
            feed.error ? null : (
              <EmptyState
                title="Nothing here yet"
                message={
                  debouncedSearch || category
                    ? 'No pieces match that. Try clearing the filters.'
                    : 'New drops land regularly — check back soon.'
                }
                action={
                  debouncedSearch || category
                    ? {
                        label: 'Clear filters',
                        onPress: () => {
                          setSearch('');
                          setCategory(null);
                        },
                      }
                    : undefined
                }
              />
            )
          }
          renderItem={({ item }) => (
            <ProductCard product={item} onPress={openProduct} width={cardWidth} />
          )}
        />
      )}
    </SafeAreaView>
  );
}

function Chip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      style={[styles.chip, active && styles.chipActive]}
    >
      <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: HORIZONTAL_PADDING, paddingTop: spacing.md },
  wordmark: { ...type.overline, color: colors.primary, marginBottom: spacing.sm },
  searchWrap: { paddingHorizontal: HORIZONTAL_PADDING, marginTop: spacing.md },
  search: {
    borderWidth: 1,
    borderColor: colors.borderLight,
    color: colors.textMain,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 15,
  },
  chipRow: {
    paddingHorizontal: HORIZONTAL_PADDING,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  chip: {
    borderWidth: 1,
    borderColor: colors.borderLight,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  chipActive: { borderColor: colors.primary, backgroundColor: 'rgba(57, 255, 20, 0.1)' },
  chipLabel: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  chipLabelActive: { color: colors.primary },
  list: { paddingHorizontal: HORIZONTAL_PADDING, paddingTop: spacing.sm, paddingBottom: spacing.xxl },
  column: { gap: GRID_GAP },
});

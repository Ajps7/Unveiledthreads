import React, { useCallback, useMemo } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { wishlist as wishlistApi } from '../api/endpoints';
import type { Product } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import type { MainTabParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { ProductCard } from '../components/ProductCard';
import { EmptyState, ErrorNotice, Loading } from '../components/ui';

const GRID_GAP = spacing.md;
const HORIZONTAL_PADDING = spacing.lg;

export function WishlistScreen() {
  const navigation = useNavigation<BottomTabNavigationProp<MainTabParamList>>();
  const { width } = useWindowDimensions();

  const saved = useAsyncData<Product[]>((signal) => wishlistApi.list(signal), []);

  const cardWidth = useMemo(
    () => Math.floor((width - HORIZONTAL_PADDING * 2 - GRID_GAP) / 2),
    [width],
  );

  const openProduct = useCallback(
    (product: Product) =>
      navigation.navigate('ShopTab', {
        screen: 'ProductDetail',
        params: { productId: product.id, productName: product.name },
      }),
    [navigation],
  );

  const items = saved.data ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={type.h1}>Wishlist</Text>
        <Text style={type.body}>
          {items.length > 0
            ? `${items.length} piece${items.length === 1 ? '' : 's'} saved`
            : 'Pieces you save appear here'}
        </Text>
      </View>

      {saved.loading && !saved.data ? (
        <Loading />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          numColumns={2}
          columnWrapperStyle={styles.column}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={saved.refreshing}
              onRefresh={saved.refresh}
              tintColor={colors.primary}
            />
          }
          ListHeaderComponent={
            saved.error ? <ErrorNotice message={saved.error} onRetry={saved.reload} /> : null
          }
          ListEmptyComponent={
            saved.error ? null : (
              <EmptyState
                title="Nothing saved yet"
                message="Tap the heart on any piece to keep it here. Saving does not reserve stock — popular drops go fast."
                action={{
                  label: 'Browse the shop',
                  onPress: () => navigation.navigate('ShopTab', { screen: 'Shop' }),
                }}
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

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: HORIZONTAL_PADDING, paddingTop: spacing.md, paddingBottom: spacing.sm },
  list: { paddingHorizontal: HORIZONTAL_PADDING, paddingTop: spacing.sm, paddingBottom: spacing.xxl },
  column: { gap: GRID_GAP },
});

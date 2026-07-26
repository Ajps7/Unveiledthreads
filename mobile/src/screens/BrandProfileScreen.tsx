import React, { useCallback, useMemo } from 'react';
import {
  FlatList,
  Image,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { resolveImageUrl } from '../api/config';
import { brands as brandsApi } from '../api/endpoints';
import type { Brand, Product } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import type { MainTabParamList, ShopStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { ProductCard } from '../components/ProductCard';
import { Badge, Button, EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<ShopStackParamList, 'BrandProfile'>;

const GRID_GAP = spacing.md;
const HORIZONTAL_PADDING = spacing.lg;

export function BrandProfileScreen({ route, navigation }: Props) {
  const { brandId } = route.params;
  const { width } = useWindowDimensions();

  const brand = useAsyncData<Brand>((signal) => brandsApi.get(brandId, signal), [brandId]);

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

  const messageBrand = useCallback(() => {
    const data = brand.data;
    if (!data) return;
    // Conversations are between users, so the recipient is the brand's owner.
    navigation.getParent<BottomTabNavigationProp<MainTabParamList>>()?.navigate('MessagesTab', {
      screen: 'Conversation',
      params: {
        conversationId: null,
        title: data.brand_name,
        recipientId: data.user_id,
      },
    });
  }, [brand.data, navigation]);

  if (brand.loading && !brand.data) return <Loading />;

  if (brand.error && !brand.data) {
    return (
      <SafeAreaView style={styles.screen} edges={['left', 'right']}>
        <View style={styles.padded}>
          <ErrorNotice message={brand.error} onRetry={brand.reload} />
        </View>
      </SafeAreaView>
    );
  }

  const data = brand.data;
  if (!data) return null;

  const banner = resolveImageUrl(data.banner_url);
  const logo = resolveImageUrl(data.logo_url);
  const products = data.products ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['left', 'right']}>
      <FlatList
        data={products}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={styles.column}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View>
            {banner ? (
              <Image source={{ uri: banner }} style={styles.banner} resizeMode="cover" />
            ) : (
              <View style={[styles.banner, styles.bannerFallback]} />
            )}

            <View style={styles.header}>
              <View style={styles.identity}>
                <View style={styles.logoWrap}>
                  {logo ? (
                    <Image source={{ uri: logo }} style={styles.logo} resizeMode="cover" />
                  ) : (
                    <Text style={styles.logoFallback}>
                      {data.brand_name.slice(0, 2).toUpperCase()}
                    </Text>
                  )}
                </View>
                <View style={styles.identityText}>
                  <Text style={type.h2}>{data.brand_name}</Text>
                  {!!data.location && <Text style={styles.location}>{data.location}</Text>}
                </View>
              </View>

              <View style={styles.badges}>
                {!!data.is_brand_of_week && <Badge>Brand of the week</Badge>}
                {data.stripe_charges_enabled === false && (
                  <Badge tone="warning">Not yet selling</Badge>
                )}
              </View>

              {!!data.description && <Text style={styles.description}>{data.description}</Text>}

              <View style={styles.action}>
                <Button label="Message this brand" variant="secondary" onPress={messageBrand} />
              </View>

              <Text style={[type.overline, styles.sectionLabel]}>
                {products.length} piece{products.length === 1 ? '' : 's'}
              </Text>
            </View>
          </View>
        }
        ListEmptyComponent={
          <EmptyState
            title="No pieces listed"
            message={`${data.brand_name} has not listed anything yet. Message them if you are after something specific.`}
          />
        }
        renderItem={({ item }) => (
          <ProductCard product={item} onPress={openProduct} width={cardWidth} />
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  padded: { padding: spacing.lg },
  list: { paddingHorizontal: HORIZONTAL_PADDING, paddingBottom: spacing.xxl },
  column: { gap: GRID_GAP },
  banner: {
    height: 140,
    marginHorizontal: -HORIZONTAL_PADDING,
    backgroundColor: colors.surface,
  },
  bannerFallback: { borderBottomWidth: 1, borderBottomColor: colors.border },
  header: { paddingTop: spacing.md },
  identity: { flexDirection: 'row', alignItems: 'center' },
  logoWrap: {
    width: 64,
    height: 64,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  logo: { width: '100%', height: '100%' },
  logoFallback: { ...type.overline, color: colors.secondary, fontSize: 16 },
  identityText: { flex: 1 },
  location: { color: colors.textMuted, fontSize: 13, marginTop: 2 },
  badges: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },
  description: { ...type.body, marginTop: spacing.md },
  action: { marginTop: spacing.lg },
  sectionLabel: { marginTop: spacing.xl, marginBottom: spacing.md },
});

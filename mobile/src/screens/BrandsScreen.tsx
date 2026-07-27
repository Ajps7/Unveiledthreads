import React from 'react';
import { FlatList, Image, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { resolveImageUrl } from '../api/config';
import { brands as brandsApi } from '../api/endpoints';
import type { Brand } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import type { ShopStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Badge, EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<ShopStackParamList, 'Brands'>;

export function BrandsScreen({ navigation }: Props) {
  const list = useAsyncData<Brand[]>((signal) => brandsApi.list(signal), []);
  const items = list.data ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['left', 'right']}>
      {list.loading && !list.data ? (
        <Loading />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={list.refreshing}
              onRefresh={list.refresh}
              tintColor={colors.primary}
            />
          }
          ListHeaderComponent={
            list.error ? <ErrorNotice message={list.error} onRetry={list.reload} /> : null
          }
          ListEmptyComponent={
            list.error ? null : (
              <EmptyState
                title="No brands yet"
                message="Independent UK brands are being onboarded — check back shortly."
              />
            )
          }
          renderItem={({ item }) => {
            const logo = resolveImageUrl(item.logo_url);
            return (
              <Pressable
                onPress={() =>
                  navigation.navigate('BrandProfile', {
                    brandId: item.id,
                    brandName: item.brand_name,
                  })
                }
                accessibilityRole="button"
                style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
              >
                <View style={styles.logoWrap}>
                  {logo ? (
                    <Image source={{ uri: logo }} style={styles.logo} resizeMode="cover" />
                  ) : (
                    <Text style={styles.logoFallback}>
                      {item.brand_name.slice(0, 2).toUpperCase()}
                    </Text>
                  )}
                </View>

                <View style={styles.info}>
                  <Text style={styles.name} numberOfLines={1}>
                    {item.brand_name}
                  </Text>
                  {!!item.location && <Text style={styles.location}>{item.location}</Text>}
                  <View style={styles.badges}>
                    {!!item.is_brand_of_week && <Badge>Brand of the week</Badge>}
                    {!!item.is_boosted && <Badge tone="muted">Boosted</Badge>}
                  </View>
                </View>
              </Pressable>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  list: { paddingBottom: spacing.xxl },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowPressed: { backgroundColor: colors.surface },
  logoWrap: {
    width: 56,
    height: 56,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  logo: { width: '100%', height: '100%' },
  logoFallback: { ...type.overline, color: colors.secondary, fontSize: 14 },
  info: { flex: 1 },
  name: { color: colors.textMain, fontSize: 16, fontWeight: '700' },
  location: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  badges: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm },
});

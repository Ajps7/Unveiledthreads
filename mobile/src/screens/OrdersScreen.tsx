import React from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { orders as ordersApi } from '../api/endpoints';
import type { Order } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import { gbp, shortDate, shippingLabel } from '../lib/format';
import type { MainTabParamList, OrdersStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Badge, EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<OrdersStackParamList, 'Orders'>;

/**
 * Only orders that reached `paid` represent a real purchase. Sessions that were
 * abandoned sit at initiated/unpaid/expired and would only confuse a buyer, so
 * they are filtered out rather than shown as pending.
 */
function isRealOrder(order: Order): boolean {
  return order.status === 'paid';
}

export function OrdersScreen({ navigation }: Props) {
  const list = useAsyncData<Order[]>((signal) => ordersApi.mine(signal), []);
  const paid = (list.data ?? []).filter(isRealOrder);

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={type.h1}>My orders</Text>
      </View>

      {list.loading && !list.data ? (
        <Loading />
      ) : (
        <FlatList
          data={paid}
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
                title="No orders yet"
                message="When you buy something it shows up here with live tracking."
                action={{
                  label: 'Browse the shop',
                  onPress: () =>
                    navigation
                      .getParent<BottomTabNavigationProp<MainTabParamList>>()
                      ?.navigate('ShopTab', { screen: 'Shop' }),
                }}
              />
            )
          }
          renderItem={({ item }) => (
            <Pressable
              onPress={() => navigation.navigate('OrderDetail', { orderId: item.id })}
              accessibilityRole="button"
              style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
            >
              <View style={styles.cardTop}>
                <View style={styles.cardTitle}>
                  <Text style={type.overline}>{item.brand_name}</Text>
                  <Text style={styles.productName} numberOfLines={1}>
                    {item.product_name}
                  </Text>
                </View>
                <Text style={styles.total}>{gbp(item.total_charged)}</Text>
              </View>

              <View style={styles.cardBottom}>
                <Badge tone={item.shipping_status === 'delivered' ? 'accent' : 'muted'}>
                  {shippingLabel(item.shipping_status)}
                </Badge>
                <Text style={styles.meta}>
                  Size {item.size} · {shortDate(item.created_at)}
                </Text>
              </View>
            </Pressable>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.sm },
  list: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xxl },
  card: { borderWidth: 1, borderColor: colors.borderLight, padding: spacing.md, marginBottom: spacing.md },
  cardPressed: { borderColor: colors.primary },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardTitle: { flex: 1, marginRight: spacing.md },
  productName: { color: colors.textMain, fontSize: 15, fontWeight: '700', marginTop: 2 },
  total: { color: colors.primary, fontSize: 15, fontWeight: '800' },
  cardBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.md,
  },
  meta: { color: colors.textMuted, fontSize: 12 },
});

import React, { useCallback } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { notifications as notificationsApi } from '../api/endpoints';
import type { Notification } from '../api/types';
import { useAsyncData } from '../hooks/useAsyncData';
import { relativeTime } from '../lib/format';
import { colors, spacing, type } from '../theme';
import { EmptyState, ErrorNotice, Loading } from '../components/ui';

export function NotificationsScreen() {
  const list = useAsyncData<Notification[]>((signal) => notificationsApi.list(signal), []);

  const markRead = useCallback(
    async (item: Notification) => {
      if (item.read) return;

      // Optimistic — the badge and row should update instantly.
      list.setData((current) =>
        (current ?? []).map((candidate) =>
          candidate.id === item.id ? { ...candidate, read: true } : candidate,
        ),
      );

      try {
        await notificationsApi.markRead(item.id);
      } catch {
        list.setData((current) =>
          (current ?? []).map((candidate) =>
            candidate.id === item.id ? { ...candidate, read: false } : candidate,
          ),
        );
      }
    },
    [list],
  );

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
                title="Nothing new"
                message="Order updates, replies and approvals land here."
              />
            )
          }
          renderItem={({ item }) => (
            <Pressable
              onPress={() => void markRead(item)}
              accessibilityRole="button"
              style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
            >
              <View style={[styles.unreadDot, item.read && styles.unreadDotRead]} />
              <View style={styles.content}>
                <Text style={[styles.title, !item.read && styles.titleUnread]} numberOfLines={2}>
                  {item.title}
                </Text>
                <Text style={styles.message} numberOfLines={3}>
                  {item.message}
                </Text>
                <Text style={styles.time}>{relativeTime(item.created_at)}</Text>
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
  list: { paddingBottom: spacing.xxl },
  row: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowPressed: { backgroundColor: colors.surface },
  unreadDot: {
    width: 7,
    height: 7,
    backgroundColor: colors.primary,
    marginTop: 6,
    marginRight: spacing.md,
  },
  unreadDotRead: { backgroundColor: 'transparent' },
  content: { flex: 1 },
  title: { color: colors.textMuted, fontSize: 14, fontWeight: '600' },
  titleUnread: { color: colors.textMain, fontWeight: '700' },
  message: { ...type.body, fontSize: 13, marginTop: 2 },
  time: { color: colors.textMuted, fontSize: 11, marginTop: spacing.sm },
});

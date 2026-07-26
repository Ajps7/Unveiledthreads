import React from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { messaging } from '../api/endpoints';
import { conversationTitle, otherParticipantId, type Conversation } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { useAsyncData } from '../hooks/useAsyncData';
import { relativeTime } from '../lib/format';
import type { MessagesStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Badge, EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<MessagesStackParamList, 'Conversations'>;

export function ConversationsScreen({ navigation }: Props) {
  const { user } = useAuth();
  const list = useAsyncData<Conversation[]>((signal) => messaging.conversations(signal), []);

  const threads = list.data ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={type.h1}>Messages</Text>
      </View>

      {list.loading && !list.data ? (
        <Loading />
      ) : (
        <FlatList
          data={threads}
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
                title="No messages"
                message="Questions about sizing or a drop? Message a brand from their product page and the thread appears here."
              />
            )
          }
          renderItem={({ item }) => {
            const title = conversationTitle(item);
            const unread = item.unread_count ?? 0;
            return (
              <Pressable
                onPress={() =>
                  navigation.navigate('Conversation', {
                    conversationId: item.id,
                    title,
                    recipientId: otherParticipantId(item, user?.id ?? ''),
                  })
                }
                accessibilityRole="button"
                style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
              >
                <View style={styles.rowMain}>
                  <Text style={styles.title} numberOfLines={1}>
                    {title}
                  </Text>
                  <Text style={styles.preview} numberOfLines={1}>
                    {item.last_message || 'No messages yet'}
                  </Text>
                </View>
                <View style={styles.rowSide}>
                  {unread > 0 && <Badge>{String(unread)}</Badge>}
                  <Text style={styles.time}>{relativeTime(item.last_message_at)}</Text>
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
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.sm },
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
  rowMain: { flex: 1, marginRight: spacing.md },
  title: { color: colors.textMain, fontSize: 15, fontWeight: '700' },
  preview: { color: colors.textMuted, fontSize: 13, marginTop: 2 },
  rowSide: { alignItems: 'flex-end', gap: spacing.xs },
  time: { color: colors.textMuted, fontSize: 11 },
});

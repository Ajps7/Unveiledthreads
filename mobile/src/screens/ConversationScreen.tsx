import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { messaging } from '../api/endpoints';
import type { Message } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { messageFromError, useAsyncData } from '../hooks/useAsyncData';
import { relativeTime } from '../lib/format';
import type { MessagesStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<MessagesStackParamList, 'Conversation'>;

/**
 * Message content is scanned server-side (scan_message in backend/core.py) for
 * contact details and off-platform payment terms. A blocked message comes back
 * as a 400 with the platform's wording — we show that verbatim rather than
 * writing our own, so the rule reads the same everywhere.
 */
export function ConversationScreen({ route, navigation }: Props) {
  const { title, recipientId } = route.params;
  const { user } = useAuth();
  const listRef = useRef<FlatList<Message>>(null);

  /**
   * Null when the thread does not exist yet ("Message this brand" from a
   * product or brand page). The backend creates the conversation on first
   * send and returns the message with its `conversation_id`, which we adopt
   * so subsequent loads work normally.
   */
  const [conversationId, setConversationId] = useState<string | null>(
    route.params.conversationId,
  );

  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const thread = useAsyncData<Message[]>(
    async (signal) => (conversationId ? messaging.messages(conversationId, signal) : []),
    [conversationId],
  );

  useEffect(() => {
    navigation.setOptions({ title });
  }, [navigation, title]);

  const messages = thread.data ?? [];

  const handleSend = useCallback(async () => {
    const content = draft.trim();
    if (!content || sending) return;

    setSending(true);
    setSendError(null);
    try {
      const sent = await messaging.send(recipientId, content);
      setDraft('');

      if (!conversationId && sent.conversation_id) {
        // First message in a new thread — adopting the id re-runs the loader.
        setConversationId(sent.conversation_id);
      } else {
        thread.reload();
      }
    } catch (error) {
      setSendError(messageFromError(error));
    } finally {
      setSending(false);
    }
  }, [draft, sending, recipientId, conversationId, thread]);

  if (thread.loading && !thread.data) return <Loading />;

  return (
    <SafeAreaView style={styles.screen} edges={['left', 'right', 'bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
          ListHeaderComponent={
            thread.error ? <ErrorNotice message={thread.error} onRetry={thread.reload} /> : null
          }
          ListEmptyComponent={
            thread.error ? null : (
              <View style={styles.empty}>
                <Text style={type.body}>
                  No messages yet. Keep the conversation and the sale on Unveiled Threads — that is
                  what Buyer Protection covers.
                </Text>
              </View>
            )
          }
          renderItem={({ item }) => {
            const mine = item.sender_id === user?.id;
            return (
              <View style={[styles.bubbleRow, mine ? styles.bubbleRowMine : styles.bubbleRowTheirs]}>
                <View style={[styles.bubble, mine ? styles.bubbleMine : styles.bubbleTheirs]}>
                  {!mine && <Text style={styles.sender}>{item.sender_name}</Text>}
                  <Text style={[styles.messageText, mine && styles.messageTextMine]}>
                    {item.content}
                  </Text>
                  <Text style={[styles.timestamp, mine && styles.timestampMine]}>
                    {relativeTime(item.created_at)}
                  </Text>
                </View>
              </View>
            );
          }}
        />

        {!!sendError && (
          <View style={styles.errorWrap}>
            <ErrorNotice message={sendError} />
          </View>
        )}

        <View style={styles.composer}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder="Write a message"
            placeholderTextColor="#4B5563"
            style={styles.input}
            multiline
            maxLength={2000}
            editable={!sending}
            accessibilityLabel="Message text"
          />
          <Pressable
            onPress={handleSend}
            disabled={!draft.trim() || sending}
            accessibilityRole="button"
            style={[styles.send, (!draft.trim() || sending) && styles.sendDisabled]}
          >
            <Text style={styles.sendLabel}>{sending ? '···' : 'SEND'}</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  list: { padding: spacing.md, paddingBottom: spacing.lg },
  empty: { padding: spacing.lg },

  bubbleRow: { flexDirection: 'row', marginBottom: spacing.sm },
  bubbleRowMine: { justifyContent: 'flex-end' },
  bubbleRowTheirs: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '80%', borderWidth: 1, padding: spacing.sm + 2 },
  bubbleMine: { backgroundColor: colors.primary, borderColor: colors.primary },
  bubbleTheirs: { backgroundColor: colors.surface, borderColor: colors.borderLight },
  sender: { ...type.overline, fontSize: 9, marginBottom: 4 },
  messageText: { color: colors.textMain, fontSize: 15, lineHeight: 21 },
  messageTextMine: { color: colors.primaryText },
  timestamp: { color: colors.textMuted, fontSize: 10, marginTop: 6 },
  timestampMine: { color: 'rgba(0, 0, 0, 0.6)' },

  errorWrap: { paddingHorizontal: spacing.md },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  input: {
    flex: 1,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: colors.borderLight,
    color: colors.textMain,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 15,
  },
  send: {
    paddingHorizontal: spacing.md,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
  },
  sendDisabled: { opacity: 0.4 },
  sendLabel: { color: colors.primaryText, fontWeight: '800', fontSize: 12, letterSpacing: 1.5 },
});

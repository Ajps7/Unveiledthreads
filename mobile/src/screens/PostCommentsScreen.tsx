import React, { useCallback, useState } from 'react';
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
import { community } from '../api/endpoints';
import type { PostComment } from '../api/types';
import { messageFromError, useAsyncData } from '../hooks/useAsyncData';
import { relativeTime } from '../lib/format';
import type { CommunityStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<CommunityStackParamList, 'PostComments'>;

export function PostCommentsScreen({ route }: Props) {
  const { postId } = route.params;
  const thread = useAsyncData<PostComment[]>(
    (signal) => community.comments(postId, signal),
    [postId],
  );

  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const handleSend = useCallback(async () => {
    const content = draft.trim();
    if (!content || sending) return;

    setSending(true);
    setSendError(null);
    try {
      await community.addComment(postId, content);
      setDraft('');
      thread.reload();
    } catch (error) {
      // Comments run through the same moderation scanner as posts and DMs.
      setSendError(messageFromError(error));
    } finally {
      setSending(false);
    }
  }, [draft, sending, postId, thread]);

  if (thread.loading && !thread.data) return <Loading />;

  const comments = thread.data ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['left', 'right', 'bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <FlatList
          data={comments}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            thread.error ? <ErrorNotice message={thread.error} onRetry={thread.reload} /> : null
          }
          ListEmptyComponent={
            thread.error ? null : (
              <EmptyState title="No replies yet" message="Say something useful." />
            )
          }
          renderItem={({ item }) => (
            <View style={styles.comment}>
              <View style={styles.commentHeader}>
                <Text style={styles.author}>{item.user_name}</Text>
                <Text style={styles.time}>{relativeTime(item.created_at)}</Text>
              </View>
              <Text style={styles.content}>{item.content}</Text>
            </View>
          )}
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
            placeholder="Add a reply"
            placeholderTextColor="#4B5563"
            style={styles.input}
            multiline
            maxLength={1000}
            editable={!sending}
            accessibilityLabel="Reply text"
          />
          <Pressable
            onPress={handleSend}
            disabled={!draft.trim() || sending}
            accessibilityRole="button"
            style={[styles.send, (!draft.trim() || sending) && styles.disabled]}
          >
            <Text style={styles.sendLabel}>{sending ? '···' : 'REPLY'}</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  list: { padding: spacing.lg, paddingBottom: spacing.lg },
  comment: { borderBottomWidth: 1, borderBottomColor: colors.border, paddingVertical: spacing.md },
  commentHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  author: { ...type.overline, fontSize: 10, color: colors.secondary },
  time: { color: colors.textMuted, fontSize: 11 },
  content: { color: colors.textMain, fontSize: 15, lineHeight: 21, marginTop: spacing.xs },
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
  disabled: { opacity: 0.4 },
  sendLabel: { color: colors.primaryText, fontWeight: '800', fontSize: 11, letterSpacing: 1.5 },
});

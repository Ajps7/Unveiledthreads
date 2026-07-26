import React, { useCallback, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { community } from '../api/endpoints';
import type { CommunityPost } from '../api/types';
import { useAuth } from '../context/AuthContext';
import { messageFromError, useAsyncData } from '../hooks/useAsyncData';
import { relativeTime } from '../lib/format';
import type { CommunityStackParamList } from '../navigation/types';
import { colors, spacing, type } from '../theme';
import { Badge, EmptyState, ErrorNotice, Loading } from '../components/ui';

type Props = NativeStackScreenProps<CommunityStackParamList, 'Community'>;

const MAX_POST_LENGTH = 1000;

export function CommunityScreen({ navigation }: Props) {
  const { user } = useAuth();
  const feed = useAsyncData<CommunityPost[]>((signal) => community.posts(signal), []);

  const [draft, setDraft] = useState('');
  const [posting, setPosting] = useState(false);
  const [composeError, setComposeError] = useState<string | null>(null);

  const handlePost = useCallback(async () => {
    const content = draft.trim();
    if (!content || posting) return;

    setPosting(true);
    setComposeError(null);
    try {
      await community.createPost(content);
      setDraft('');
      feed.reload();
    } catch (error) {
      // A 400 here is usually the moderation scanner rejecting contact details
      // or off-platform payment terms. Its wording is the platform's, so show
      // it as-is rather than paraphrasing the rule.
      setComposeError(messageFromError(error));
    } finally {
      setPosting(false);
    }
  }, [draft, posting, feed]);

  /**
   * Likes are stored as an array of user ids on the post. Toggle optimistically
   * against the local copy, then roll back if the server disagrees.
   */
  const toggleLike = useCallback(
    async (post: CommunityPost) => {
      if (!user) return;
      const liked = post.likes?.includes(user.id) ?? false;

      feed.setData((current) =>
        (current ?? []).map((candidate) =>
          candidate.id === post.id
            ? {
                ...candidate,
                likes: liked
                  ? candidate.likes.filter((id) => id !== user.id)
                  : [...candidate.likes, user.id],
              }
            : candidate,
        ),
      );

      try {
        await community.toggleLike(post.id);
      } catch {
        feed.setData((current) =>
          (current ?? []).map((candidate) =>
            candidate.id === post.id
              ? {
                  ...candidate,
                  likes: liked
                    ? [...candidate.likes, user.id]
                    : candidate.likes.filter((id) => id !== user.id),
                }
              : candidate,
          ),
        );
      }
    },
    [feed, user],
  );

  const posts = feed.data ?? [];

  return (
    <SafeAreaView style={styles.screen} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={type.h1}>Community</Text>
      </View>

      {feed.loading && !feed.data ? (
        <Loading />
      ) : (
        <FlatList
          data={posts}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={feed.refreshing}
              onRefresh={feed.refresh}
              tintColor={colors.primary}
            />
          }
          ListHeaderComponent={
            <View>
              <View style={styles.composer}>
                <TextInput
                  value={draft}
                  onChangeText={setDraft}
                  placeholder="Share a fit, a find, or a question"
                  placeholderTextColor="#4B5563"
                  style={styles.composerInput}
                  multiline
                  maxLength={MAX_POST_LENGTH}
                  editable={!posting}
                  accessibilityLabel="New post"
                />
                <View style={styles.composerFooter}>
                  <Text style={styles.counter}>
                    {draft.length}/{MAX_POST_LENGTH}
                  </Text>
                  <Pressable
                    onPress={handlePost}
                    disabled={!draft.trim() || posting}
                    accessibilityRole="button"
                    style={[styles.postButton, (!draft.trim() || posting) && styles.disabled]}
                  >
                    <Text style={styles.postButtonLabel}>{posting ? '···' : 'POST'}</Text>
                  </Pressable>
                </View>
              </View>

              {!!composeError && <ErrorNotice message={composeError} />}
              {!!feed.error && <ErrorNotice message={feed.error} onRetry={feed.reload} />}
            </View>
          }
          ListEmptyComponent={
            feed.error ? null : (
              <EmptyState
                title="Quiet in here"
                message="Be the first to post. Fit pics, questions about sizing, or a brand you rate."
              />
            )
          }
          renderItem={({ item }) => {
            const liked = user ? (item.likes?.includes(user.id) ?? false) : false;
            const likeCount = item.likes?.length ?? 0;

            return (
              <View style={styles.post}>
                <View style={styles.postHeader}>
                  <Text style={styles.author}>{item.brand_name || item.user_name}</Text>
                  {!!item.brand_name && <Badge>Brand</Badge>}
                  <Text style={styles.postTime}>{relativeTime(item.created_at)}</Text>
                </View>

                <Text style={styles.postContent}>{item.content}</Text>

                {!!item.brand_tag && (
                  <View style={styles.tagRow}>
                    <Badge tone="muted">{item.brand_tag}</Badge>
                  </View>
                )}

                <View style={styles.postActions}>
                  <Pressable
                    onPress={() => void toggleLike(item)}
                    accessibilityRole="button"
                    accessibilityLabel={liked ? 'Unlike post' : 'Like post'}
                    style={styles.action}
                  >
                    <Text style={[styles.actionText, liked && styles.actionTextActive]}>
                      {liked ? '♥' : '♡'} {likeCount}
                    </Text>
                  </Pressable>

                  <Pressable
                    onPress={() => navigation.navigate('PostComments', { postId: item.id })}
                    accessibilityRole="button"
                    style={styles.action}
                  >
                    <Text style={styles.actionText}>💬 {item.comment_count ?? 0}</Text>
                  </Pressable>
                </View>
              </View>
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
  list: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xxl },

  composer: { borderWidth: 1, borderColor: colors.borderLight, marginBottom: spacing.lg },
  composerInput: {
    color: colors.textMain,
    padding: spacing.md,
    fontSize: 15,
    minHeight: 84,
    textAlignVertical: 'top',
  },
  composerFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  counter: { color: colors.textMuted, fontSize: 11 },
  postButton: { backgroundColor: colors.primary, paddingHorizontal: spacing.md, paddingVertical: 8 },
  disabled: { opacity: 0.4 },
  postButtonLabel: {
    color: colors.primaryText,
    fontWeight: '800',
    fontSize: 11,
    letterSpacing: 1.5,
  },

  post: {
    borderWidth: 1,
    borderColor: colors.borderLight,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  postHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  author: { color: colors.textMain, fontSize: 14, fontWeight: '700' },
  postTime: { color: colors.textMuted, fontSize: 11, marginLeft: 'auto' },
  postContent: { color: colors.textMain, fontSize: 15, lineHeight: 22, marginTop: spacing.sm },
  tagRow: { flexDirection: 'row', marginTop: spacing.sm },
  postActions: { flexDirection: 'row', gap: spacing.lg, marginTop: spacing.md },
  action: { paddingVertical: 4 },
  actionText: { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
  actionTextActive: { color: colors.primary },
});

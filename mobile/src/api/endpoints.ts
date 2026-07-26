import { api, type QueryParams } from './client';
import { WEB_BASE_URL } from './config';
import type {
  Brand,
  CheckoutResponse,
  CommunityPost,
  Conversation,
  FilterOptions,
  Message,
  Notification,
  Order,
  OrderStatusResponse,
  PollResponse,
  PostComment,
  Product,
  ProductFilters,
  User,
} from './types';

/**
 * One function per API route the app uses. Screens call these, never `api`
 * directly — so a backend contract change lands in exactly one file.
 */

// ---------- auth ----------

export const auth = {
  me: () => api.get<User>('/api/auth/me'),

  login: (email: string, password: string) =>
    api.post<User>('/api/auth/login', { email, password }),

  register: (email: string, password: string, name: string) =>
    api.post<User>('/api/auth/register', { email, password, name }),

  logout: () => api.post<{ message: string }>('/api/auth/logout'),

  forgotPassword: (email: string) =>
    api.post<{ message: string }>('/api/auth/forgot-password', { email }),

  /**
   * Added alongside the password-policy work — lets a signed-in user rotate
   * their password without the email reset round trip.
   */
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<{ message: string }>('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};

// ---------- catalogue ----------

/**
 * ProductFilters is a closed interface (so typos are caught at the call site),
 * which means it has no index signature and is not directly assignable to
 * QueryParams. Every field is already a string/number/boolean/undefined, so
 * widening here is sound — the narrow type has done its job by this point.
 */
function toQueryParams(filters: ProductFilters, extra: QueryParams = {}): QueryParams {
  return { ...filters, ...extra } as QueryParams;
}

export const products = {
  list: (filters: ProductFilters = {}, signal?: AbortSignal) =>
    api.get<Product[]>(
      '/api/products',
      // Dead stock lives in its own section; never mix it into the main shop.
      toQueryParams(filters, { is_dead_stock: false }),
      signal,
    ),

  deadStock: (filters: ProductFilters = {}, signal?: AbortSignal) =>
    api.get<Product[]>('/api/dead-stock', toQueryParams(filters), signal),

  get: (productId: string, signal?: AbortSignal) =>
    api.get<Product>(`/api/products/${productId}`, undefined, signal),

  filterOptions: (signal?: AbortSignal) =>
    api.get<FilterOptions>('/api/products/filter-options', undefined, signal),

  categories: (signal?: AbortSignal) =>
    api.get<string[]>('/api/categories', undefined, signal),

  /** Fire-and-forget view counter; failures are not worth surfacing. */
  trackView: (productId: string) =>
    api.post(`/api/analytics/view/${productId}`).catch(() => undefined),
};

export const brands = {
  list: (signal?: AbortSignal) => api.get<Brand[]>('/api/brands', undefined, signal),
  get: (brandId: string, signal?: AbortSignal) =>
    api.get<Brand>(`/api/brands/${brandId}`, undefined, signal),
  boosted: (signal?: AbortSignal) => api.get<Brand[]>('/api/brands/boosted', undefined, signal),
  brandOfWeek: (signal?: AbortSignal) =>
    api.get<Brand | null>('/api/brands/brand-of-week', undefined, signal),
};

// ---------- wishlist ----------

export const wishlist = {
  list: (signal?: AbortSignal) => api.get<Product[]>('/api/wishlist', undefined, signal),
  ids: (signal?: AbortSignal) => api.get<string[]>('/api/wishlist/ids', undefined, signal),
  add: (productId: string) => api.post<{ in_wishlist: boolean }>(`/api/wishlist/${productId}`),
  remove: (productId: string) => api.delete<{ in_wishlist: boolean }>(`/api/wishlist/${productId}`),
};

// ---------- orders ----------

export const orders = {
  mine: (signal?: AbortSignal) => api.get<Order[]>('/api/orders/my-orders', undefined, signal),

  /**
   * Starts a Stripe Checkout session and returns its hosted URL.
   *
   * `origin_url` is the WEB origin, not a deep link: the backend builds
   * success/cancel redirects from it, and Stripe needs somewhere real to land.
   * The app opens the returned URL in an in-app browser and, once dismissed,
   * polls `status()` to find out what actually happened — we never trust the
   * redirect itself as proof of payment.
   */
  checkout: (productId: string, size: string) =>
    api.post<CheckoutResponse>('/api/orders/checkout', {
      product_id: productId,
      size,
      origin_url: WEB_BASE_URL,
    }),

  status: (sessionId: string) =>
    api.get<OrderStatusResponse>(`/api/orders/status/${sessionId}`),
};

// ---------- messaging ----------

export const messaging = {
  conversations: (signal?: AbortSignal) =>
    api.get<Conversation[]>('/api/conversations', undefined, signal),

  messages: (conversationId: string, signal?: AbortSignal) =>
    api.get<Message[]>(`/api/conversations/${conversationId}/messages`, undefined, signal),

  send: (recipientId: string, content: string, orderId?: string) =>
    api.post<Message>('/api/messages/send', {
      recipient_id: recipientId,
      content,
      ...(orderId ? { order_id: orderId } : {}),
    }),

  unreadCount: (signal?: AbortSignal) =>
    api.get<{ count: number }>('/api/messages/unread-count', undefined, signal),
};

// ---------- notifications ----------

export const notifications = {
  list: (signal?: AbortSignal) =>
    api.get<Notification[]>('/api/notifications', undefined, signal),

  unreadCount: (signal?: AbortSignal) =>
    api.get<{ count: number }>('/api/notifications/unread-count', undefined, signal),

  markRead: (notificationId: string) =>
    api.post<{ message: string }>(`/api/notifications/${notificationId}/read`),

  /** Unread notification + message counts in one call, for the tab badges. */
  poll: (signal?: AbortSignal) =>
    api.get<PollResponse>('/api/notifications/poll', undefined, signal),
};

// ---------- community ----------

export const community = {
  posts: (signal?: AbortSignal) =>
    api.get<CommunityPost[]>('/api/community/posts', undefined, signal),

  createPost: (content: string, brandTag?: string) =>
    api.post<CommunityPost>('/api/community/posts', {
      content,
      ...(brandTag ? { brand_tag: brandTag } : {}),
    }),

  toggleLike: (postId: string) =>
    api.post<{ liked: boolean; like_count: number }>(`/api/community/posts/${postId}/like`),

  comments: (postId: string, signal?: AbortSignal) =>
    api.get<PostComment[]>(`/api/community/posts/${postId}/comments`, undefined, signal),

  addComment: (postId: string, content: string) =>
    api.post<PostComment>(`/api/community/posts/${postId}/comments`, { content }),

  deletePost: (postId: string) =>
    api.delete<{ message: string }>(`/api/community/posts/${postId}`),
};

// ---------- account (UK GDPR self-service) ----------

export const account = {
  /** Article 20 data export. Returns the full JSON dump for this user. */
  export: () => api.get<Record<string, unknown>>('/api/account/export'),

  /**
   * Article 17 erasure. The backend model is `{password, confirm}` and
   * `confirm` must be exactly "DELETE" — do not rename these fields.
   */
  delete: (password: string) =>
    api.post<{ message: string }>('/api/account/delete', {
      password,
      confirm: 'DELETE',
    }),
};

/**
 * Response shapes as the API actually returns them today. Mongo documents are
 * returned largely verbatim with `_id` renamed to `id`, so most fields are
 * optional — treat anything not written on every code path as possibly absent.
 */

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'brand' | 'admin';
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  category: string;
  sizes: string[];
  images: string[];
  stock: number;
  shipping_cost: number;
  brand_id: string;
  brand_name: string;
  colour?: string | null;
  material?: string | null;
  gender?: string;
  condition?: string;
  fit?: string | null;
  is_dead_stock?: boolean;
  /** Brand has finished Stripe Connect onboarding — false means it cannot sell yet. */
  seller_payments_ready?: boolean;
  created_at?: string;
}

export interface Brand {
  id: string;
  brand_name: string;
  slug?: string;
  description?: string;
  location?: string;
  category?: string;
  logo_url?: string | null;
  banner_url?: string | null;
  is_boosted?: boolean;
  is_brand_of_week?: boolean;
  products?: Product[];
}

export interface ShippingUpdate {
  status: string;
  note?: string;
  timestamp: string;
}

export interface Order {
  id: string;
  session_id: string;
  product_id: string;
  product_name: string;
  brand_id: string;
  brand_name: string;
  size: string;
  price: number;
  shipping_cost: number;
  platform_fee: number;
  credit_applied?: number;
  total_charged: number;
  status: 'initiated' | 'unpaid' | 'paid' | 'expired' | string;
  shipping_status?: string;
  tracking_number?: string | null;
  courier?: string | null;
  shipping_updates?: ShippingUpdate[];
  reviewed?: boolean;
  created_at: string;
}

/** Receipt object returned alongside order status polls. */
export interface OrderReceipt {
  price: number;
  platform_fee: number;
  shipping: number;
  credit_applied?: number;
  total: number;
}

export interface OrderStatusResponse {
  status: string;
  payment_status: string;
  already_processed?: boolean;
  order?: OrderReceipt;
}

export interface CheckoutResponse {
  url: string;
  session_id: string;
}

export interface Conversation {
  id: string;
  participant_1: string;
  participant_2: string;
  /**
   * The other participant's user document, minus `_id` and `password_hash`.
   * It therefore has NO id field — derive the recipient id from
   * participant_1/participant_2 instead. See otherParticipantId() below.
   */
  other_user?: { name?: string; email?: string; role?: string } | null;
  other_brand_name?: string | null;
  last_message?: string;
  last_message_at?: string;
  unread_count?: number;
}

/** The conversation payload omits the other user's id, so derive it. */
export function otherParticipantId(conversation: Conversation, myUserId: string): string {
  return conversation.participant_1 === myUserId
    ? conversation.participant_2
    : conversation.participant_1;
}

/** Brand name when the other side is a seller, otherwise their display name. */
export function conversationTitle(conversation: Conversation): string {
  return conversation.other_brand_name || conversation.other_user?.name || 'Unveiled Threads user';
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  flagged?: boolean;
  read?: boolean;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface FilterOptions {
  sizes?: string[];
  colours?: string[];
  materials?: string[];
  categories?: string[];
  fits?: string[];
}

export interface ProductFilters {
  category?: string;
  search?: string;
  size?: string;
  colour?: string;
  gender?: string;
  condition?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  sort?: 'latest' | 'price_low' | 'price_high' | 'popular';
  limit?: number;
  skip?: number;
}

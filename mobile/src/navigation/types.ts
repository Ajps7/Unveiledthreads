import type { NavigatorScreenParams } from '@react-navigation/native';

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};

export type ShopStackParamList = {
  Shop: undefined;
  ProductDetail: { productId: string; productName?: string };
  Brands: undefined;
  BrandProfile: { brandId: string; brandName?: string };
};

export type CommunityStackParamList = {
  Community: undefined;
  PostComments: { postId: string };
};

export type MessagesStackParamList = {
  Conversations: undefined;
  /**
   * `conversationId` is null when starting a fresh thread (e.g. "Message this
   * brand" from a product). The first successful send returns a message whose
   * `conversation_id` we adopt, and the thread loads from there.
   */
  Conversation: {
    conversationId: string | null;
    title: string;
    recipientId: string;
  };
};

/**
 * Orders live under Account rather than in the tab bar — the same place Depop
 * and Vinted put purchases. Post-checkout we deep-link straight to Orders, so
 * the path that actually matters stays one tap.
 */
export type AccountStackParamList = {
  Account: undefined;
  Orders: undefined;
  OrderDetail: { orderId: string };
  Notifications: undefined;
  ChangePassword: undefined;
};

export type MainTabParamList = {
  ShopTab: NavigatorScreenParams<ShopStackParamList>;
  CommunityTab: NavigatorScreenParams<CommunityStackParamList>;
  WishlistTab: undefined;
  MessagesTab: NavigatorScreenParams<MessagesStackParamList>;
  AccountTab: NavigatorScreenParams<AccountStackParamList>;
};

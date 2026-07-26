import type { NavigatorScreenParams } from '@react-navigation/native';

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};

export type ShopStackParamList = {
  Shop: undefined;
  ProductDetail: { productId: string; productName?: string };
};

export type OrdersStackParamList = {
  Orders: undefined;
  OrderDetail: { orderId: string };
};

export type MessagesStackParamList = {
  Conversations: undefined;
  Conversation: { conversationId: string; title: string; recipientId: string };
};

export type AccountStackParamList = {
  Account: undefined;
  ChangePassword: undefined;
};

export type MainTabParamList = {
  ShopTab: NavigatorScreenParams<ShopStackParamList>;
  WishlistTab: undefined;
  OrdersTab: NavigatorScreenParams<OrdersStackParamList>;
  MessagesTab: NavigatorScreenParams<MessagesStackParamList>;
  AccountTab: NavigatorScreenParams<AccountStackParamList>;
};

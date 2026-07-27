import React from 'react';
import { Text } from 'react-native';
import { NavigationContainer, DarkTheme, type Theme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useAuth } from '../context/AuthContext';
import { useUnreadBadges } from '../hooks/useUnreadBadges';
import { colors } from '../theme';
import { Loading } from '../components/ui';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { ForgotPasswordScreen } from '../screens/ForgotPasswordScreen';
import { ShopScreen } from '../screens/ShopScreen';
import { ProductDetailScreen } from '../screens/ProductDetailScreen';
import { BrandsScreen } from '../screens/BrandsScreen';
import { BrandProfileScreen } from '../screens/BrandProfileScreen';
import { CommunityScreen } from '../screens/CommunityScreen';
import { PostCommentsScreen } from '../screens/PostCommentsScreen';
import { WishlistScreen } from '../screens/WishlistScreen';
import { OrdersScreen } from '../screens/OrdersScreen';
import { OrderDetailScreen } from '../screens/OrderDetailScreen';
import { ConversationsScreen } from '../screens/ConversationsScreen';
import { ConversationScreen } from '../screens/ConversationScreen';
import { AccountScreen } from '../screens/AccountScreen';
import { NotificationsScreen } from '../screens/NotificationsScreen';
import { ChangePasswordScreen } from '../screens/ChangePasswordScreen';
import type {
  AccountStackParamList,
  AuthStackParamList,
  CommunityStackParamList,
  MainTabParamList,
  MessagesStackParamList,
  ShopStackParamList,
} from './types';

const navTheme: Theme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    primary: colors.primary,
    background: colors.background,
    card: colors.background,
    text: colors.textMain,
    border: colors.border,
    notification: colors.primary,
  },
};

const screenOptions = {
  headerStyle: { backgroundColor: colors.background },
  headerTintColor: colors.textMain,
  headerTitleStyle: { fontWeight: '700' as const, letterSpacing: 0.5 },
  headerShadowVisible: false,
  contentStyle: { backgroundColor: colors.background },
};

// ---------- auth ----------

const AuthStack = createNativeStackNavigator<AuthStackParamList>();

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ ...screenOptions, headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
      <AuthStack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
    </AuthStack.Navigator>
  );
}

// ---------- shop ----------

const ShopStack = createNativeStackNavigator<ShopStackParamList>();

function ShopNavigator() {
  return (
    <ShopStack.Navigator screenOptions={screenOptions}>
      <ShopStack.Screen name="Shop" component={ShopScreen} options={{ headerShown: false }} />
      <ShopStack.Screen
        name="ProductDetail"
        component={ProductDetailScreen}
        options={({ route }) => ({ title: route.params.productName ?? 'Piece' })}
      />
      <ShopStack.Screen name="Brands" component={BrandsScreen} options={{ title: 'Brands' }} />
      <ShopStack.Screen
        name="BrandProfile"
        component={BrandProfileScreen}
        options={({ route }) => ({ title: route.params.brandName ?? 'Brand' })}
      />
    </ShopStack.Navigator>
  );
}

// ---------- community ----------

const CommunityStack = createNativeStackNavigator<CommunityStackParamList>();

function CommunityNavigator() {
  return (
    <CommunityStack.Navigator screenOptions={screenOptions}>
      <CommunityStack.Screen
        name="Community"
        component={CommunityScreen}
        options={{ headerShown: false }}
      />
      <CommunityStack.Screen
        name="PostComments"
        component={PostCommentsScreen}
        options={{ title: 'Replies' }}
      />
    </CommunityStack.Navigator>
  );
}

// ---------- messages ----------

const MessagesStack = createNativeStackNavigator<MessagesStackParamList>();

function MessagesNavigator() {
  return (
    <MessagesStack.Navigator screenOptions={screenOptions}>
      <MessagesStack.Screen
        name="Conversations"
        component={ConversationsScreen}
        options={{ headerShown: false }}
      />
      <MessagesStack.Screen
        name="Conversation"
        component={ConversationScreen}
        options={({ route }) => ({ title: route.params.title })}
      />
    </MessagesStack.Navigator>
  );
}

// ---------- account ----------

const AccountStack = createNativeStackNavigator<AccountStackParamList>();

function AccountNavigator() {
  return (
    <AccountStack.Navigator screenOptions={screenOptions}>
      <AccountStack.Screen
        name="Account"
        component={AccountScreen}
        options={{ headerShown: false }}
      />
      <AccountStack.Screen name="Orders" component={OrdersScreen} options={{ title: 'My orders' }} />
      <AccountStack.Screen
        name="OrderDetail"
        component={OrderDetailScreen}
        options={{ title: 'Order' }}
      />
      <AccountStack.Screen
        name="Notifications"
        component={NotificationsScreen}
        options={{ title: 'Notifications' }}
      />
      <AccountStack.Screen
        name="ChangePassword"
        component={ChangePasswordScreen}
        options={{ title: 'Password' }}
      />
    </AccountStack.Navigator>
  );
}

// ---------- tabs ----------

const Tabs = createBottomTabNavigator<MainTabParamList>();

/**
 * Text glyphs instead of an icon library — one fewer dependency, and the
 * brutalist type-led design does not want soft rounded icons anyway.
 */
function TabGlyph({ glyph, focused }: { glyph: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 18, color: focused ? colors.primary : colors.textMuted }}>
      {glyph}
    </Text>
  );
}

function MainNavigator() {
  const { status } = useAuth();
  const { counts } = useUnreadBadges(status === 'authenticated');

  // react-navigation treats 0 as a visible empty badge, so pass undefined.
  const messageBadge = counts?.messages ? counts.messages : undefined;
  const notificationBadge = counts?.notifications ? counts.notifications : undefined;

  return (
    <Tabs.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.background,
          borderTopColor: colors.border,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: { fontSize: 10, fontWeight: '700', letterSpacing: 1 },
        tabBarBadgeStyle: { backgroundColor: colors.primary, color: colors.primaryText },
      }}
    >
      <Tabs.Screen
        name="ShopTab"
        component={ShopNavigator}
        options={{
          title: 'SHOP',
          tabBarIcon: ({ focused }) => <TabGlyph glyph="▣" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="CommunityTab"
        component={CommunityNavigator}
        options={{
          title: 'FEED',
          tabBarIcon: ({ focused }) => <TabGlyph glyph="◈" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="WishlistTab"
        component={WishlistScreen}
        options={{
          title: 'SAVED',
          tabBarIcon: ({ focused }) => <TabGlyph glyph="♡" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="MessagesTab"
        component={MessagesNavigator}
        options={{
          title: 'INBOX',
          tabBarBadge: messageBadge,
          tabBarIcon: ({ focused }) => <TabGlyph glyph="✉" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="AccountTab"
        component={AccountNavigator}
        options={{
          title: 'YOU',
          tabBarBadge: notificationBadge,
          tabBarIcon: ({ focused }) => <TabGlyph glyph="◉" focused={focused} />,
        }}
      />
    </Tabs.Navigator>
  );
}

export function RootNavigator() {
  const { status } = useAuth();

  return (
    <NavigationContainer theme={navTheme}>
      {status === 'loading' ? (
        // The session check is a network round trip. Holding here avoids
        // flashing the sign-in screen at a user who is already signed in.
        <Loading />
      ) : status === 'authenticated' ? (
        <MainNavigator />
      ) : (
        <AuthNavigator />
      )}
    </NavigationContainer>
  );
}

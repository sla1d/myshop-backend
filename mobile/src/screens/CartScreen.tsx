import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, Image, StyleSheet, Alert } from 'react-native';
import { getCart, removeFromCart } from '../api/client';

export default function CartScreen({ navigation }: any) {
  const [cart, setCart] = useState({ items: [], total: 0, count: 0 });

  useEffect(() => {
    loadCart();
  }, []);

  const loadCart = async () => {
    const { data } = await getCart();
    setCart(data);
  };

  const handleRemove = async (productId: number) => {
    Alert.alert('Удалить?', 'Товар будет удалён из корзины', [
      { text: 'Отмена' },
      {
        text: 'Удалить',
        onPress: async () => {
          await removeFromCart(productId);
          loadCart();
        },
      },
    ]);
  };

  if (cart.items.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>Корзина пуста</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Home')}>
          <Text style={styles.link}>Перейти в каталог</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={cart.items}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <View style={styles.item}>
            <Image source={{ uri: item.image }} style={styles.image} />
            <View style={styles.details}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.price}>{item.price} ₽ x {item.quantity}</Text>
            </View>
            <TouchableOpacity onPress={() => handleRemove(item.id)}>
              <Text style={styles.remove}>✕</Text>
            </TouchableOpacity>
          </View>
        )}
      />
      <View style={styles.footer}>
        <Text style={styles.total}>Итого: {cart.total} ₽</Text>
        <TouchableOpacity
          style={styles.checkout}
          onPress={() => navigation.navigate('Checkout')}
        >
          <Text style={styles.checkoutText}>Оформить заказ</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { fontSize: 18, color: '#666' },
  link: { fontSize: 16, color: '#667eea', marginTop: 10 },
  item: {
    flexDirection: 'row', backgroundColor: '#fff', padding: 15, marginHorizontal: 10,
    marginTop: 10, borderRadius: 10, alignItems: 'center',
  },
  image: { width: 60, height: 60, borderRadius: 8 },
  details: { flex: 1, marginLeft: 15 },
  name: { fontSize: 14, fontWeight: '500' },
  price: { fontSize: 14, color: '#667eea', marginTop: 5 },
  remove: { fontSize: 20, color: '#ff4444', padding: 10 },
  footer: {
    backgroundColor: '#fff', padding: 20, borderTopWidth: 1, borderTopColor: '#eee',
  },
  total: { fontSize: 20, fontWeight: 'bold', marginBottom: 15 },
  checkout: {
    backgroundColor: '#667eea', padding: 15, borderRadius: 10, alignItems: 'center',
  },
  checkoutText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
});

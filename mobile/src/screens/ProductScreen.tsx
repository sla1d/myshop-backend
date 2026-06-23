import React, { useEffect, useState } from 'react';
import { View, Text, Image, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { getProduct, addToCart } from '../api/client';

export default function ProductScreen({ route, navigation }: any) {
  const [product, setProduct] = useState<any>(null);
  const { id } = route.params;

  useEffect(() => {
    loadProduct();
  }, [id]);

  const loadProduct = async () => {
    const { data } = await getProduct(id);
    setProduct(data);
  };

  const handleAddToCart = async () => {
    await addToCart(id);
    alert('Добавлено в корзину!');
  };

  if (!product) return null;

  return (
    <ScrollView style={styles.container}>
      <Image source={{ uri: product.image }} style={styles.image} />
      <View style={styles.info}>
        <Text style={styles.name}>{product.name}</Text>
        <Text style={styles.brand}>{product.brand}</Text>
        <Text style={styles.price}>{product.price} ₽</Text>
        <Text style={styles.rating}>⭐ {product.rating} / 5</Text>
        <Text style={styles.category}>Категория: {product.category}</Text>
      </View>
      <TouchableOpacity style={styles.button} onPress={handleAddToCart}>
        <Text style={styles.buttonText}>В корзину</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  image: { width: '100%', height: 300 },
  info: { padding: 20 },
  name: { fontSize: 24, fontWeight: 'bold' },
  brand: { fontSize: 16, color: '#666', marginTop: 5 },
  price: { fontSize: 28, fontWeight: 'bold', color: '#667eea', marginTop: 10 },
  rating: { fontSize: 16, marginTop: 10 },
  category: { fontSize: 14, color: '#999', marginTop: 5 },
  button: {
    backgroundColor: '#667eea', margin: 20, padding: 15, borderRadius: 10, alignItems: 'center',
  },
  buttonText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
});

import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, Image, StyleSheet, ActivityIndicator } from 'react-native';
import { getProducts } from '../api/client';

export default function HomeScreen({ navigation }: any) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const { data } = await getProducts({ sort: 'rating', limit: 10 });
      setProducts(data);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <ActivityIndicator size="large" style={styles.loader} />;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Популярные товары</Text>
      <FlatList
        data={products}
        keyExtractor={(item) => String(item.id)}
        numColumns={2}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => navigation.navigate('Product', { id: item.id })}
          >
            <Image source={{ uri: item.image }} style={styles.image} />
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.price}>{item.price} ₽</Text>
            <Text style={styles.rating}>⭐ {item.rating}</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 10, backgroundColor: '#f5f5f5' },
  title: { fontSize: 20, fontWeight: 'bold', marginBottom: 15 },
  loader: { flex: 1, justifyContent: 'center' },
  card: {
    flex: 1, backgroundColor: '#fff', borderRadius: 10, padding: 10, margin: 5,
    elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1, shadowRadius: 2,
  },
  image: { width: '100%', height: 120, borderRadius: 8 },
  name: { fontSize: 14, marginTop: 8, fontWeight: '500' },
  price: { fontSize: 16, fontWeight: 'bold', marginTop: 4, color: '#667eea' },
  rating: { fontSize: 12, color: '#666', marginTop: 2 },
});

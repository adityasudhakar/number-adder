import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Linking } from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';

type Props = {
  navigation: NativeStackNavigationProp<any>;
};

export default function LandingScreen({ navigation }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Number Adder</Text>
      <Text style={styles.subtitle}>Add numbers. Upgrade to multiply.</Text>

      <View style={styles.options}>
        <TouchableOpacity
          style={styles.card}
          onPress={() => navigation.navigate('Login')}
        >
          <View style={[styles.badge, styles.cloudBadge]}>
            <Text style={styles.badgeText}>Hosted</Text>
          </View>
          <Text style={styles.cardTitle}>Cloud</Text>
          <Text style={styles.cardDescription}>
            Use instantly with no setup. We handle hosting, updates, and backups.
          </Text>
          <View style={styles.button}>
            <Text style={styles.buttonText}>Get Started</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.card}
          onPress={() => Linking.openURL('https://pypi.org/project/number-adder/')}
        >
          <View style={[styles.badge, styles.selfBadge]}>
            <Text style={[styles.badgeText, styles.selfBadgeText]}>Open Source</Text>
          </View>
          <Text style={styles.cardTitle}>Self-Hosted</Text>
          <Text style={styles.cardDescription}>
            Run on your own server. Full control over your data.
          </Text>
          <View style={styles.codeBlock}>
            <Text style={styles.codeText}>pip install number-adder</Text>
          </View>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        onPress={() => Linking.openURL('https://www.number-adder.com/privacy.html')}
      >
        <Text style={styles.link}>Privacy Policy</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#333',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginBottom: 40,
  },
  options: {
    gap: 16,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    marginBottom: 12,
  },
  cloudBadge: {
    backgroundColor: '#e3f2fd',
  },
  selfBadge: {
    backgroundColor: '#f3e5f5',
  },
  badgeText: {
    fontSize: 12,
    color: '#1976d2',
    fontWeight: '600',
  },
  selfBadgeText: {
    color: '#7b1fa2',
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  cardDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 16,
    lineHeight: 20,
  },
  button: {
    backgroundColor: '#007bff',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 6,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  codeBlock: {
    backgroundColor: '#1e1e1e',
    padding: 12,
    borderRadius: 6,
  },
  codeText: {
    color: '#d4d4d4',
    fontFamily: 'monospace',
    fontSize: 14,
  },
  link: {
    color: '#007bff',
    textAlign: 'center',
    marginTop: 24,
    fontSize: 14,
  },
});

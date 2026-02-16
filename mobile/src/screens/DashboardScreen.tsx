import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  Linking,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useAuth } from '../context/AuthContext';
import { api, Calculation } from '../api/client';

type Props = {
  navigation: NativeStackNavigationProp<any>;
};

export default function DashboardScreen({ navigation }: Props) {
  const { user, logout, refreshUser } = useAuth();
  const [a, setA] = useState('');
  const [b, setB] = useState('');
  const [result, setResult] = useState<number | null>(null);
  const [operation, setOperation] = useState<'add' | 'multiply'>('add');
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<Calculation[]>([]);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      const data = await api.getHistory();
      setHistory(data.calculations.slice(0, 5));
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  }

  async function handleCalculate() {
    const numA = parseFloat(a);
    const numB = parseFloat(b);

    if (isNaN(numA) || isNaN(numB)) {
      Alert.alert('Error', 'Please enter valid numbers');
      return;
    }

    setIsLoading(true);
    try {
      if (operation === 'add') {
        const response = await api.add(numA, numB);
        setResult(response.result);
      } else {
        const response = await api.multiply(numA, numB);
        setResult(response.result);
      }
      await loadHistory();
    } catch (error: any) {
      if (error.message.includes('Premium')) {
        Alert.alert(
          'Premium Required',
          'Multiply is a premium feature. Would you like to upgrade?',
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Upgrade', onPress: handleUpgrade },
          ]
        );
      } else {
        Alert.alert('Error', error.message);
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUpgrade() {
    try {
      const response = await api.createCheckoutSession();
      await Linking.openURL(response.checkout_url);
      // After returning from browser, refresh user data
      setTimeout(() => refreshUser(), 2000);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  }

  function handleLogout() {
    Alert.alert('Logout', 'Are you sure you want to logout?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: logout },
    ]);
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Number Adder</Text>
        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {/* User info */}
      <View style={styles.userCard}>
        <Text style={styles.userEmail}>{user?.email}</Text>
        <View style={[styles.badge, user?.is_premium ? styles.premiumBadge : styles.freeBadge]}>
          <Text style={styles.badgeText}>{user?.is_premium ? 'Premium' : 'Free'}</Text>
        </View>
      </View>

      {/* Upgrade banner */}
      {!user?.is_premium && (
        <TouchableOpacity style={styles.upgradeBanner} onPress={handleUpgrade}>
          <Text style={styles.upgradeTitle}>Upgrade to Premium</Text>
          <Text style={styles.upgradeText}>Unlock multiply and more features</Text>
        </TouchableOpacity>
      )}

      {/* Calculator */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Calculator</Text>

        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, operation === 'add' && styles.tabActive]}
            onPress={() => setOperation('add')}
          >
            <Text style={[styles.tabText, operation === 'add' && styles.tabTextActive]}>
              Add (+)
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, operation === 'multiply' && styles.tabActive]}
            onPress={() => setOperation('multiply')}
          >
            <Text style={[styles.tabText, operation === 'multiply' && styles.tabTextActive]}>
              Multiply (×) {!user?.is_premium && '🔒'}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.inputRow}>
          <TextInput
            style={styles.numberInput}
            value={a}
            onChangeText={setA}
            placeholder="0"
            keyboardType="numeric"
          />
          <Text style={styles.operator}>{operation === 'add' ? '+' : '×'}</Text>
          <TextInput
            style={styles.numberInput}
            value={b}
            onChangeText={setB}
            placeholder="0"
            keyboardType="numeric"
          />
        </View>

        <TouchableOpacity
          style={[styles.calculateButton, isLoading && styles.buttonDisabled]}
          onPress={handleCalculate}
          onLongPress={() => Alert.alert("Calculate", "Sends your numbers to the server and returns the result.")}
          delayLongPress={300}
          disabled={isLoading}
          accessibilityRole="button"
          accessibilityHint="Calculates the result for the two numbers"
        >
          <Text style={styles.calculateButtonText}>
            {isLoading ? 'Calculating...' : 'Calculate'}
          </Text>
        </TouchableOpacity>

        {result !== null && (
          <View style={styles.resultBox}>
            <Text style={styles.resultLabel}>Result</Text>
            <Text style={styles.resultValue}>{result}</Text>
          </View>
        )}
      </View>

      {/* History */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Recent History</Text>
        {history.length === 0 ? (
          <Text style={styles.emptyText}>No calculations yet</Text>
        ) : (
          history.map((calc) => (
            <View key={calc.id} style={styles.historyItem}>
              <Text style={styles.historyCalc}>
                {calc.a} {calc.operation === 'add' ? '+' : '×'} {calc.b} = {calc.result}
              </Text>
              <Text style={styles.historyDate}>
                {new Date(calc.created_at).toLocaleDateString()}
              </Text>
            </View>
          ))
        )}
      </View>

      {/* Settings link */}
      <TouchableOpacity
        style={styles.settingsLink}
        onPress={() => navigation.navigate('Settings')}
      >
        <Text style={styles.settingsText}>Settings & Privacy</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 60,
    backgroundColor: 'white',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  logoutText: {
    color: '#007bff',
    fontSize: 16,
  },
  userCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 8,
  },
  userEmail: {
    fontSize: 16,
    color: '#333',
  },
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
  },
  freeBadge: {
    backgroundColor: '#e0e0e0',
  },
  premiumBadge: {
    backgroundColor: '#ffd700',
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
  },
  upgradeBanner: {
    backgroundColor: '#007bff',
    margin: 16,
    padding: 16,
    borderRadius: 8,
  },
  upgradeTitle: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  upgradeText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 14,
    marginTop: 4,
  },
  card: {
    backgroundColor: 'white',
    margin: 16,
    marginTop: 0,
    padding: 20,
    borderRadius: 8,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  tabs: {
    flexDirection: 'row',
    marginBottom: 20,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
    padding: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 6,
  },
  tabActive: {
    backgroundColor: 'white',
  },
  tabText: {
    color: '#666',
    fontSize: 14,
    fontWeight: '500',
  },
  tabTextActive: {
    color: '#007bff',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  numberInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 16,
    fontSize: 24,
    textAlign: 'center',
  },
  operator: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
    marginHorizontal: 16,
  },
  calculateButton: {
    backgroundColor: '#007bff',
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  calculateButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '600',
  },
  resultBox: {
    backgroundColor: '#f0f8ff',
    padding: 20,
    borderRadius: 8,
    marginTop: 20,
    alignItems: 'center',
  },
  resultLabel: {
    color: '#666',
    fontSize: 14,
    marginBottom: 8,
  },
  resultValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#007bff',
  },
  emptyText: {
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  historyItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  historyCalc: {
    fontSize: 16,
    color: '#333',
  },
  historyDate: {
    fontSize: 12,
    color: '#999',
  },
  settingsLink: {
    alignItems: 'center',
    padding: 20,
    marginBottom: 40,
  },
  settingsText: {
    color: '#007bff',
    fontSize: 16,
  },
});

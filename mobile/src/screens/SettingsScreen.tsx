import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  Linking,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const [userData, setUserData] = useState<any>(null);
  const [showData, setShowData] = useState(false);

  async function handleViewData() {
    try {
      const data = await api.exportData();
      setUserData(data);
      setShowData(true);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  }

  async function handleExportData() {
    try {
      const data = await api.exportData();
      Alert.alert(
        'Your Data',
        JSON.stringify(data, null, 2),
        [{ text: 'OK' }]
      );
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  }

  function handleDeleteAccount() {
    Alert.alert(
      'Delete Account',
      'This will permanently delete your account and all associated data. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.deleteAccount();
              await logout();
              Alert.alert('Success', 'Your account has been deleted');
            } catch (error: any) {
              Alert.alert('Error', error.message);
            }
          },
        },
      ]
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.label}>Email</Text>
            <Text style={styles.value}>{user?.email}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Status</Text>
            <Text style={styles.value}>{user?.is_premium ? 'Premium' : 'Free'}</Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Privacy (GDPR)</Text>
        <View style={styles.card}>
          <TouchableOpacity style={styles.menuItem} onPress={handleViewData}>
            <Text style={styles.menuText}>View My Data</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem} onPress={handleExportData}>
            <Text style={styles.menuText}>Export My Data</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => Linking.openURL('https://www.number-adder.com/privacy.html')}
          >
            <Text style={styles.menuText}>Privacy Policy</Text>
            <Text style={styles.menuArrow}>›</Text>
          </TouchableOpacity>
        </View>
      </View>

      {showData && userData && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Your Data</Text>
          <View style={styles.dataCard}>
            <Text style={styles.dataText}>
              {JSON.stringify(userData, null, 2)}
            </Text>
          </View>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Danger Zone</Text>
        <TouchableOpacity style={styles.deleteButton} onPress={handleDeleteAccount}>
          <Text style={styles.deleteButtonText}>Delete Account</Text>
        </TouchableOpacity>
        <Text style={styles.dangerNote}>
          This will permanently delete your account and all associated data.
        </Text>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Number Adder v1.0.0</Text>
        <TouchableOpacity
          onPress={() => Linking.openURL('https://github.com/adityasudhakar/number-adder')}
        >
          <Text style={styles.footerLink}>GitHub</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    marginBottom: 8,
    marginLeft: 4,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 10,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  label: {
    fontSize: 16,
    color: '#333',
  },
  value: {
    fontSize: 16,
    color: '#666',
  },
  menuItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  menuText: {
    fontSize: 16,
    color: '#333',
  },
  menuArrow: {
    fontSize: 20,
    color: '#ccc',
  },
  dataCard: {
    backgroundColor: '#1e1e1e',
    borderRadius: 10,
    padding: 16,
  },
  dataText: {
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#d4d4d4',
  },
  deleteButton: {
    backgroundColor: '#dc3545',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
  },
  deleteButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  dangerNote: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
  },
  footer: {
    alignItems: 'center',
    padding: 40,
  },
  footerText: {
    fontSize: 14,
    color: '#999',
  },
  footerLink: {
    fontSize: 14,
    color: '#007bff',
    marginTop: 8,
  },
});

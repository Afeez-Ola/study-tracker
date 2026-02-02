import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Alert,
  Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const App = () => {
  const [topic, setTopic] = useState('');
  const [isActive, setIsActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState({
    totalSessions: 0,
    totalMinutes: 0,
    streak: 0,
  });

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    let interval = null;
    if (isActive && !isPaused) {
      interval = setInterval(() => {
        setSeconds(s => s + 1);
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isActive, isPaused]);

  const loadSessions = async () => {
    try {
      const stored = await AsyncStorage.getItem('study_sessions');
      if (stored) {
        const parsed = JSON.parse(stored);
        setSessions(parsed);
        calculateStats(parsed);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  const calculateStats = (sessionsData) => {
    const total = sessionsData.length;
    const totalMins = sessionsData.reduce((sum, s) => sum + s.minutes, 0);
    
    // Calculate streak
    const dates = [...new Set(sessionsData.map(s => s.date))].sort().reverse();
    let streak = 0;
    const today = new Date().toISOString().split('T')[0];
    let checkDate = new Date(today);
    
    for (let i = 0; i < 365; i++) {
      const dateStr = checkDate.toISOString().split('T')[0];
      if (dates.includes(dateStr)) {
        streak++;
        checkDate.setDate(checkDate.getDate() - 1);
      } else if (i > 0) {
        break;
      } else {
        checkDate.setDate(checkDate.getDate() - 1);
      }
    }
    
    setStats({ totalSessions: total, totalMinutes: totalMins, streak });
  };

  const startSession = () => {
    if (!topic.trim()) {
      Alert.alert('Error', 'Please enter what you\'re studying!');
      return;
    }
    setIsActive(true);
    setIsPaused(false);
    setSeconds(0);
  };

  const pauseSession = () => {
    setIsPaused(!isPaused);
  };

  const stopSession = async () => {
    const minutes = Math.floor(seconds / 60);
    
    if (minutes === 0) {
      Alert.alert('Too Short', 'Study for at least 1 minute before saving!');
      return;
    }

    const session = {
      id: Date.now(),
      topic: topic.trim(),
      minutes: minutes,
      date: new Date().toISOString().split('T')[0],
      timestamp: new Date().toISOString(),
    };

    try {
      const newSessions = [session, ...sessions];
      await AsyncStorage.setItem('study_sessions', JSON.stringify(newSessions));
      setSessions(newSessions);
      calculateStats(newSessions);
      
      Alert.alert(
        'Session Saved! 🎉',
        `Topic: ${topic}\nTime: ${minutes} minutes`,
        [{ text: 'OK' }]
      );
      
      // Reset
      setIsActive(false);
      setIsPaused(false);
      setSeconds(0);
      setTopic('');
    } catch (error) {
      Alert.alert('Error', 'Failed to save session');
    }
  };

  const formatTime = (secs) => {
    const hours = Math.floor(secs / 3600);
    const minutes = Math.floor((secs % 3600) / 60);
    const seconds = secs % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  const exportCSV = async () => {
    try {
      const csv = [
        'Topic,Minutes,Date,Timestamp',
        ...sessions.map(s => `"${s.topic}",${s.minutes},${s.date},${s.timestamp}`)
      ].join('\n');
      
      // On mobile, you'd use react-native-share or similar
      Alert.alert('Export', 'CSV data ready:\n\n' + csv.substring(0, 200) + '...');
    } catch (error) {
      Alert.alert('Error', 'Failed to export');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0d1117" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>⏱️ Study Tracker</Text>
        <Text style={styles.subtitle}>Mobile Edition</Text>

        {/* Stats Cards */}
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.streak}</Text>
            <Text style={styles.statLabel}>Day Streak 🔥</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.totalSessions}</Text>
            <Text style={styles.statLabel}>Sessions</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.totalMinutes}</Text>
            <Text style={styles.statLabel}>Total Minutes</Text>
          </View>
        </View>

        {/* Input Section */}
        <View style={styles.inputSection}>
          <Text style={styles.inputLabel}>What are you studying?</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., Python Programming"
            placeholderTextColor="#8b949e"
            value={topic}
            onChangeText={setTopic}
            editable={!isActive}
          />
        </View>

        {/* Timer Display */}
        <View style={styles.timerSection}>
          <Text style={styles.timer}>{formatTime(seconds)}</Text>
          <Text style={[styles.status, isActive && !isPaused && styles.statusActive]}>
            {isActive ? (isPaused ? 'Paused' : 'In Progress...') : 'Ready to Start'}
          </Text>
        </View>

        {/* Control Buttons */}
        <View style={styles.controls}>
          {!isActive ? (
            <TouchableOpacity style={styles.btnStart} onPress={startSession}>
              <Text style={styles.btnText}>Start Session</Text>
            </TouchableOpacity>
          ) : (
            <>
              <TouchableOpacity style={styles.btnPause} onPress={pauseSession}>
                <Text style={styles.btnText}>{isPaused ? 'Resume' : 'Pause'}</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.btnStop} onPress={stopSession}>
                <Text style={styles.btnText}>Finish</Text>
              </TouchableOpacity>
            </>
          )}
        </View>

        {/* Note */}
        <View style={styles.note}>
          <Text style={styles.noteText}>
            <Text style={styles.noteBold}>Note:</Text> Mobile apps cannot track system-wide activity. 
            This version uses manual timer tracking. Start when you begin studying, 
            stop when you finish!
          </Text>
        </View>

        {/* Recent Sessions */}
        <View style={styles.historySection}>
          <Text style={styles.historyTitle}>Recent Sessions</Text>
          {sessions.length === 0 ? (
            <Text style={styles.emptyText}>No sessions yet. Start studying!</Text>
          ) : (
            sessions.slice(0, 10).map(session => (
              <View key={session.id} style={styles.sessionCard}>
                <View style={styles.sessionHeader}>
                  <Text style={styles.sessionTopic}>{session.topic}</Text>
                  <Text style={styles.sessionDate}>{session.date}</Text>
                </View>
                <Text style={styles.sessionMeta}>{session.minutes} minutes</Text>
              </View>
            ))
          )}
        </View>

        {/* Export Button */}
        <TouchableOpacity style={styles.btnExport} onPress={exportCSV}>
          <Text style={styles.btnText}>📥 Export Data</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1117',
  },
  scrollContent: {
    padding: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#58a6ff',
    textAlign: 'center',
    marginTop: 20,
  },
  subtitle: {
    fontSize: 16,
    color: '#8b949e',
    textAlign: 'center',
    marginBottom: 20,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#161b22',
    borderRadius: 8,
    padding: 15,
    marginHorizontal: 5,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#58a6ff',
  },
  statLabel: {
    fontSize: 12,
    color: '#8b949e',
    marginTop: 5,
  },
  inputSection: {
    backgroundColor: '#161b22',
    borderRadius: 8,
    padding: 20,
    marginBottom: 20,
  },
  inputLabel: {
    color: '#c9d1d9',
    fontWeight: '600',
    marginBottom: 10,
  },
  input: {
    backgroundColor: '#0d1117',
    borderWidth: 1,
    borderColor: '#30363d',
    borderRadius: 6,
    padding: 12,
    color: '#c9d1d9',
    fontSize: 16,
  },
  timerSection: {
    backgroundColor: '#161b22',
    borderRadius: 8,
    padding: 40,
    alignItems: 'center',
    marginBottom: 20,
  },
  timer: {
    fontSize: 56,
    fontWeight: 'bold',
    color: '#58a6ff',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  status: {
    fontSize: 16,
    color: '#8b949e',
    marginTop: 10,
  },
  statusActive: {
    color: '#3fb950',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 10,
    marginBottom: 20,
  },
  btnStart: {
    backgroundColor: '#238636',
    paddingVertical: 15,
    paddingHorizontal: 40,
    borderRadius: 8,
    flex: 1,
  },
  btnPause: {
    backgroundColor: '#bb8009',
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 8,
    flex: 1,
    marginRight: 5,
  },
  btnStop: {
    backgroundColor: '#da3633',
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 8,
    flex: 1,
    marginLeft: 5,
  },
  btnText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  note: {
    backgroundColor: 'rgba(187, 128, 9, 0.1)',
    borderWidth: 1,
    borderColor: '#bb8009',
    borderRadius: 6,
    padding: 15,
    marginBottom: 20,
  },
  noteText: {
    color: '#d29922',
    lineHeight: 20,
  },
  noteBold: {
    fontWeight: 'bold',
  },
  historySection: {
    marginBottom: 20,
  },
  historyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#c9d1d9',
    marginBottom: 15,
  },
  emptyText: {
    color: '#8b949e',
    textAlign: 'center',
    paddingVertical: 20,
  },
  sessionCard: {
    backgroundColor: '#161b22',
    borderWidth: 1,
    borderColor: '#30363d',
    borderRadius: 6,
    padding: 15,
    marginBottom: 10,
  },
  sessionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 5,
  },
  sessionTopic: {
    color: '#58a6ff',
    fontWeight: '600',
    flex: 1,
  },
  sessionDate: {
    color: '#8b949e',
    fontSize: 12,
  },
  sessionMeta: {
    color: '#8b949e',
    fontSize: 14,
  },
  btnExport: {
    backgroundColor: '#238636',
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 8,
    marginBottom: 30,
  },
});

export default App;

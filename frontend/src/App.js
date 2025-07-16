import React, { useState, useEffect, useContext, createContext } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Create Auth Context
const AuthContext = createContext();

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user profile:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { username, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const register = async (username, email, password) => {
    try {
      const response = await axios.post(`${API}/auth/register`, { username, email, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const value = {
    user,
    token,
    login,
    register,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Theme Context
const ThemeContext = createContext();

const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');

  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Login Component
const Login = ({ onSwitchToRegister }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(username, password);
    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">Giriş Yap</h2>
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Kullanıcı Adı</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Şifre</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="form-input"
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
          </button>
        </form>
        <p className="auth-switch">
          Hesabın yok mu?{' '}
          <button onClick={onSwitchToRegister} className="link-button">
            Kayıt Ol
          </button>
        </p>
      </div>
    </div>
  );
};

// Register Component
const Register = ({ onSwitchToLogin }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await register(username, email, password);
    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">Kayıt Ol</h2>
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Kullanıcı Adı</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">E-posta</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Şifre</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="form-input"
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Kayıt olunuyor...' : 'Kayıt Ol'}
          </button>
        </form>
        <p className="auth-switch">
          Zaten hesabın var mı?{' '}
          <button onClick={onSwitchToLogin} className="link-button">
            Giriş Yap
          </button>
        </p>
      </div>
    </div>
  );
};

// Header Component
const Header = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="header">
      <div className="header-container">
        <h1 className="logo">📚 E-Sınav Sistemi</h1>
        <div className="header-actions">
          <button onClick={toggleTheme} className="theme-toggle">
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <span className="user-info">Hoş geldin, {user?.username}!</span>
          <button onClick={logout} className="logout-button">
            Çıkış Yap
          </button>
        </div>
      </div>
    </header>
  );
};

// Dashboard Component
const Dashboard = ({ onStartExam }) => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setProfile(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Yükleniyor...</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Kontrol Paneli</h2>
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Toplam Sınav</h3>
            <p className="stat-number">{profile?.total_exams || 0}</p>
          </div>
          <div className="stat-card">
            <h3>Ortalama Puan</h3>
            <p className="stat-number">{profile?.average_score?.toFixed(1) || 0}%</p>
          </div>
          <div className="stat-card">
            <h3>Rozetler</h3>
            <p className="stat-number">{user?.badges?.length || 0}</p>
          </div>
        </div>
      </div>

      <div className="dashboard-actions">
        <button className="action-button primary" onClick={onStartExam}>
          🎯 Yeni Sınav Başlat
        </button>
        <button className="action-button secondary">
          📊 Sınav Geçmişi
        </button>
        <button className="action-button secondary">
          🏆 Lider Tablosu
        </button>
      </div>

      {profile?.recent_sessions?.length > 0 && (
        <div className="recent-sessions">
          <h3>Son Sınavlar</h3>
          <div className="sessions-grid">
            {profile.recent_sessions.map((session) => (
              <div key={session.id} className="session-card">
                <p className="session-score">Puan: {session.score?.toFixed(1)}%</p>
                <p className="session-date">
                  {new Date(session.completed_at).toLocaleDateString('tr-TR')}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Exam Component
const Exam = ({ onExamComplete }) => {
  const [examData, setExamData] = useState(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    startExam();
  }, []);

  useEffect(() => {
    if (timeLeft > 0) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    } else if (timeLeft === 0 && examData) {
      submitExam();
    }
  }, [timeLeft, examData]);

  const startExam = async () => {
    try {
      const response = await axios.post(`${API}/exam/start?num_questions=5`);
      setExamData(response.data);
      setTimeLeft(response.data.time_limit * 60); // Convert to seconds
      setLoading(false);
    } catch (error) {
      console.error('Error starting exam:', error);
      setLoading(false);
    }
  };

  const handleAnswerSelect = async (questionId, optionIndex) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [questionId]: optionIndex
    }));

    try {
      await axios.post(`${API}/exam/${examData.session_id}/answer`, {
        question_id: questionId,
        selected_option: optionIndex
      });
    } catch (error) {
      console.error('Error submitting answer:', error);
    }
  };

  const submitExam = async () => {
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/exam/${examData.session_id}/submit`);
      onExamComplete(response.data);
    } catch (error) {
      console.error('Error submitting exam:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return <div className="loading">Sınav hazırlanıyor...</div>;
  }

  if (!examData) {
    return <div className="error">Sınav yüklenemedi. Lütfen tekrar deneyin.</div>;
  }

  const currentQuestion = examData.questions[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / examData.questions.length) * 100;

  return (
    <div className="exam-container">
      <div className="exam-header">
        <div className="exam-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">
            {currentQuestionIndex + 1} / {examData.questions.length}
          </span>
        </div>
        <div className="exam-timer">
          ⏱️ {formatTime(timeLeft)}
        </div>
      </div>

      <div className="question-card">
        <h3 className="question-text">{currentQuestion.text}</h3>
        
        {currentQuestion.image_url && (
          <img 
            src={currentQuestion.image_url} 
            alt="Question" 
            className="question-image"
          />
        )}

        <div className="options-grid">
          {currentQuestion.options.map((option, index) => (
            <button
              key={index}
              className={`option-button ${
                selectedAnswers[currentQuestion.id] === index ? 'selected' : ''
              }`}
              onClick={() => handleAnswerSelect(currentQuestion.id, index)}
            >
              <span className="option-letter">{String.fromCharCode(65 + index)}</span>
              <span className="option-text">{option}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="exam-navigation">
        <button
          onClick={() => setCurrentQuestionIndex(Math.max(0, currentQuestionIndex - 1))}
          disabled={currentQuestionIndex === 0}
          className="nav-button"
        >
          ← Önceki
        </button>
        
        {currentQuestionIndex < examData.questions.length - 1 ? (
          <button
            onClick={() => setCurrentQuestionIndex(currentQuestionIndex + 1)}
            className="nav-button"
          >
            Sonraki →
          </button>
        ) : (
          <button
            onClick={submitExam}
            disabled={submitting}
            className="submit-button"
          >
            {submitting ? 'Gönderiliyor...' : 'Sınavı Bitir'}
          </button>
        )}
      </div>
    </div>
  );
};

// Exam Results Component
const ExamResults = ({ results, onReturnToDashboard }) => {
  const { result, new_badges } = results;

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Sınav Sonuçları</h2>
        <div className="score-display">
          <div className="score-circle">
            <span className="score-number">{result.score.toFixed(1)}%</span>
          </div>
          <div className="score-details">
            <p>✅ Doğru: {result.correct_answers}</p>
            <p>❌ Yanlış: {result.incorrect_answers}</p>
            <p>⏱️ Süre: {result.time_taken} dakika</p>
          </div>
        </div>
      </div>

      {new_badges && new_badges.length > 0 && (
        <div className="new-badges">
          <h3>🏆 Yeni Rozetler!</h3>
          <div className="badges-grid">
            {new_badges.map((badge, index) => (
              <div key={index} className="badge-card">
                {badge}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="detailed-results">
        <h3>Detaylı Sonuçlar</h3>
        <div className="questions-results">
          {result.detailed_results.map((question, index) => (
            <div
              key={question.question_id}
              className={`question-result ${question.is_correct ? 'correct' : 'incorrect'}`}
            >
              <div className="question-header">
                <span className="question-number">#{index + 1}</span>
                <span className={`result-icon ${question.is_correct ? 'correct' : 'incorrect'}`}>
                  {question.is_correct ? '✅' : '❌'}
                </span>
              </div>
              <p className="question-text">{question.question_text}</p>
              <div className="answer-info">
                <p><strong>Seçtiğiniz:</strong> {question.options[question.user_answer]}</p>
                <p><strong>Doğru cevap:</strong> {question.options[question.correct_answer]}</p>
                <p className="explanation">{question.explanation}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="results-actions">
        <button onClick={onReturnToDashboard} className="action-button primary">
          Ana Sayfaya Dön
        </button>
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  const [currentView, setCurrentView] = useState('dashboard');
  const [authView, setAuthView] = useState('login');
  const [examResults, setExamResults] = useState(null);
  const { user, loading } = useAuth();

  useEffect(() => {
    // Initialize questions on first load
    const initializeApp = async () => {
      try {
        await axios.post(`${API}/admin/init`);
      } catch (error) {
        console.error('Error initializing app:', error);
      }
    };

    if (user) {
      initializeApp();
    }
  }, [user]);

  const handleExamComplete = (results) => {
    setExamResults(results);
    setCurrentView('results');
  };

  const handleReturnToDashboard = () => {
    setCurrentView('dashboard');
    setExamResults(null);
  };

  if (loading) {
    return (
      <div className="app">
        <div className="loading">Yükleniyor...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="app">
        {authView === 'login' ? (
          <Login onSwitchToRegister={() => setAuthView('register')} />
        ) : (
          <Register onSwitchToLogin={() => setAuthView('login')} />
        )}
      </div>
    );
  }

  return (
    <div className="app">
      <Header />
      <main className="main-content">
        {currentView === 'dashboard' && (
          <Dashboard onStartExam={() => setCurrentView('exam')} />
        )}
        {currentView === 'exam' && (
          <Exam onExamComplete={handleExamComplete} />
        )}
        {currentView === 'results' && examResults && (
          <ExamResults
            results={examResults}
            onReturnToDashboard={handleReturnToDashboard}
          />
        )}
      </main>
    </div>
  );
};

// App with Providers
const AppWithProviders = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ThemeProvider>
  );
};

export default AppWithProviders;
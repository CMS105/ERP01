import React, { useState, useEffect } from 'react';
import { useLanguage } from './i18n/LanguageContext';
import { api, Booking, DeliveryTask } from './services/api';
import { storage } from './services/storage';
import Header from './components/Header';
import CustomerHomeScreen from './screens/customer/HomeScreen';
import BookingScreen from './screens/customer/BookingScreen';
import OrderDetailsScreen from './screens/customer/OrderDetailsScreen';
import OrderHistoryScreen from './screens/customer/OrderHistoryScreen';
import ProfileScreen from './screens/customer/ProfileScreen';
import DeliveryTaskListScreen from './screens/delivery/DeliveryTaskListScreen';
import DeliveryTaskDetailScreen from './screens/delivery/DeliveryTaskDetailScreen';
import DeliveryOutcomeScreen from './screens/delivery/DeliveryOutcomeScreen';
import { Home, PlusCircle, Clock, User, Package, LogIn, Flame } from 'lucide-react';

const App: React.FC = () => {
  const { t } = useLanguage();
  const [role, setRole] = useState<'CUSTOMER' | 'DELIVERY_BOY'>((storage.getUserRole() as any) || 'CUSTOMER');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!storage.getToken());
  const [customerTab, setCustomerTab] = useState<'home' | 'book' | 'history' | 'profile' | 'detail'>('home');
  const [deliveryView, setDeliveryView] = useState<'list' | 'detail' | 'outcome' | 'profile'>('list');
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [selectedTask, setSelectedTask] = useState<DeliveryTask | null>(null);
  const [pendingSyncCount, setPendingSyncCount] = useState<number>(storage.getQueuedOutcomes().length);
  const [loginEmail, setLoginEmail] = useState('customer1@example.com');
  const [loginPassword, setLoginPassword] = useState('Pass123!');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  useEffect(() => {
    setPendingSyncCount(storage.getQueuedOutcomes().length);
  }, [deliveryView, customerTab]);

  const handleLogin = async (emailToUse?: string, passToUse?: string, targetRole?: 'CUSTOMER' | 'DELIVERY_BOY') => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const email = emailToUse || loginEmail;
      const pass = passToUse || loginPassword;
      const res = await api.login(email, pass);
      setIsAuthenticated(true);
      const userRole = targetRole || (res.role as any);
      setRole(userRole);
      storage.setUserRole(userRole);
      if (userRole === 'CUSTOMER') {
        setCustomerTab('home');
      } else {
        setDeliveryView('list');
      }
    } catch {
      setLoginError('Login failed. Please check credentials or backend connection.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    storage.clearToken();
    setIsAuthenticated(false);
  };

  const handleSwitchRole = () => {
    const nextRole = role === 'CUSTOMER' ? 'DELIVERY_BOY' : 'CUSTOMER';
    setRole(nextRole);
    storage.setUserRole(nextRole);
    if (nextRole === 'CUSTOMER') {
      setLoginEmail('customer1@example.com');
      setCustomerTab('home');
    } else {
      setLoginEmail('driver1@example.com');
      setDeliveryView('list');
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="mobile-shell">
        <div style={{ padding: '24px 16px', minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center', marginBottom: '28px' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '20px',
                background: 'linear-gradient(135deg, var(--color-terracotta), var(--color-marigold))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px auto',
                boxShadow: 'var(--shadow-clay-primary)'
              }}
            >
              <Flame size={36} color="#fff" />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 900, color: 'var(--color-primary-text)' }}>
              LPG Suvidha
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--color-secondary-text)', marginTop: '4px' }}>
              Clean Energy • Reliable Deliveries
            </p>
          </div>

          <div className="clay-card" style={{ padding: '24px', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '17px', fontWeight: 800, marginBottom: '16px', color: 'var(--color-primary-text)' }}>
              {t('login') || 'Login'}
            </h2>

            {loginError && (
              <div style={{ fontSize: '12px', color: 'var(--color-error)', background: 'rgba(192,57,43,0.1)', padding: '10px', borderRadius: '10px', marginBottom: '14px' }}>
                {loginError}
              </div>
            )}

            <form onSubmit={e => { e.preventDefault(); handleLogin(); }}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '6px' }}>
                  Email
                </label>
                <input
                  type="email"
                  className="clay-input"
                  value={loginEmail}
                  onChange={e => setLoginEmail(e.target.value)}
                  style={{ width: '100%' }}
                  required
                />
              </div>

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '6px' }}>
                  Password
                </label>
                <input
                  type="password"
                  className="clay-input"
                  value={loginPassword}
                  onChange={e => setLoginPassword(e.target.value)}
                  style={{ width: '100%' }}
                  required
                />
              </div>

              <button
                type="submit"
                className="clay-button"
                disabled={isLoggingIn}
                style={{ width: '100%', padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <LogIn size={16} />
                <span>{isLoggingIn ? (t('loading') || 'Loading...') : (t('login') || 'Login')}</span>
              </button>
            </form>
          </div>

          <div className="clay-card" style={{ padding: '16px', textAlign: 'center' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '10px' }}>
              Demo Quick-Switch Logins
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => handleLogin('customer1@example.com', 'Pass123!', 'CUSTOMER')}
                className="clay-button-secondary"
                style={{ flex: 1, padding: '8px 4px', fontSize: '12px' }}
              >
                Customer
              </button>
              <button
                onClick={() => handleLogin('driver1@example.com', 'Pass123!', 'DELIVERY_BOY')}
                className="clay-button-secondary"
                style={{ flex: 1, padding: '8px 4px', fontSize: '12px' }}
              >
                Delivery Partner
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mobile-shell">
      <Header
        role={role}
        offlinePendingCount={pendingSyncCount}
        onSwitchRole={handleSwitchRole}
      />

      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: '80px' }}>
        {role === 'CUSTOMER' ? (
          customerTab === 'home' ? (
            <CustomerHomeScreen
              onNavigateToBooking={() => setCustomerTab('book')}
              onNavigateToHistory={() => setCustomerTab('history')}
              onSelectBooking={(booking: Booking) => {
                setSelectedBooking(booking);
                setCustomerTab('detail');
              }}
            />
          ) : customerTab === 'book' ? (
            <BookingScreen
              onBookingSuccess={(booking: Booking) => {
                setSelectedBooking(booking);
                setCustomerTab('detail');
              }}
              onBack={() => setCustomerTab('home')}
            />
          ) : customerTab === 'detail' && selectedBooking ? (
            <OrderDetailsScreen
              booking={selectedBooking}
              onBack={() => setCustomerTab('home')}
            />
          ) : customerTab === 'history' ? (
            <OrderHistoryScreen
              onSelectBooking={(booking: Booking) => {
                setSelectedBooking(booking);
                setCustomerTab('detail');
              }}
            />
          ) : (
            <ProfileScreen onLogout={handleLogout} />
          )
        ) : (
          deliveryView === 'list' ? (
            <DeliveryTaskListScreen
              onSelectTask={task => {
                setSelectedTask(task);
                setDeliveryView('detail');
              }}
              onRefreshOffline={() => setPendingSyncCount(storage.getQueuedOutcomes().length)}
            />
          ) : deliveryView === 'detail' && selectedTask ? (
            <DeliveryTaskDetailScreen
              task={selectedTask}
              onBack={() => setDeliveryView('list')}
              onProceedToOutcome={() => setDeliveryView('outcome')}
            />
          ) : deliveryView === 'outcome' && selectedTask ? (
            <DeliveryOutcomeScreen
              task={selectedTask}
              onBack={() => setDeliveryView('detail')}
              onSuccess={() => {
                setDeliveryView('list');
                setPendingSyncCount(storage.getQueuedOutcomes().length);
              }}
            />
          ) : (
            <ProfileScreen onLogout={handleLogout} />
          )
        )}
      </div>

      <nav
        style={{
          position: 'fixed',
          bottom: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '100%',
          maxWidth: '460px',
          height: '64px',
          background: 'var(--color-cream)',
          borderTop: '1px solid rgba(184, 78, 47, 0.1)',
          boxShadow: '0 -4px 16px rgba(58, 38, 24, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-around',
          zIndex: 90
        }}
      >
        {role === 'CUSTOMER' ? (
          <>
            <button
              onClick={() => setCustomerTab('home')}
              style={{
                background: 'none',
                border: 'none',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                cursor: 'pointer',
                color: customerTab === 'home' ? 'var(--color-terracotta)' : 'var(--color-secondary-text)'
              }}
            >
              <Home size={20} />
              <span style={{ fontSize: '11px', fontWeight: customerTab === 'home' ? 800 : 500 }}>{t('home') || 'Home'}</span>
            </button>

            <button
              onClick={() => setCustomerTab('book')}
              style={{
                background: 'none',
                border: 'none',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                cursor: 'pointer',
                color: customerTab === 'book' ? 'var(--color-terracotta)' : 'var(--color-secondary-text)'
              }}
            >
              <PlusCircle size={20} />
              <span style={{ fontSize: '11px', fontWeight: customerTab === 'book' ? 800 : 500 }}>{t('bookCylinder') || 'Book'}</span>
            </button>

            <button
              onClick={() => setCustomerTab('history')}
              style={{
                background: 'none',
                border: 'none',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                cursor: 'pointer',
                color: customerTab === 'history' ? 'var(--color-terracotta)' : 'var(--color-secondary-text)'
              }}
            >
              <Clock size={20} />
              <span style={{ fontSize: '11px', fontWeight: customerTab === 'history' ? 800 : 500 }}>{t('orders') || 'Orders'}</span>
            </button>

            <button
              onClick={() => setCustomerTab('profile')}
              style={{
                background: 'none',
                border: 'none',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                cursor: 'pointer',
                color: customerTab === 'profile' ? 'var(--color-terracotta)' : 'var(--color-secondary-text)'
              }}
            >
              <User size={20} />
              <span style={{ fontSize: '11px', fontWeight: customerTab === 'profile' ? 800 : 500 }}>{t('profile') || 'Profile'}</span>
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => setDeliveryView('list')}
              style={{
                background: 'none',
                border: 'none',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                cursor: 'pointer',
                color: deliveryView !== 'profile' ? 'var(--color-terracotta)' : 'var(--color-secondary-text)'
              }}
            >
              <Package size={20} />
              <span style={{ fontSize: '11px', fontWeight: deliveryView !== 'profile' ? 800 : 500 }}>{t('tasks') || 'Tasks'}</span>
            </button>

            <button
              onClick={() => setDeliveryView('profile')}
              style={{
                background: 'none',
                border: 'none',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                cursor: 'pointer',
                color: deliveryView === 'profile' ? 'var(--color-terracotta)' : 'var(--color-secondary-text)'
              }}
            >
              <User size={20} />
              <span style={{ fontSize: '11px', fontWeight: deliveryView === 'profile' ? 800 : 500 }}>{t('profile') || 'Profile'}</span>
            </button>
          </>
        )}
      </nav>
    </div>
  );
};

export default App;

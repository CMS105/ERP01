import React, { useEffect, useState } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { api, CustomerProfile } from '../../services/api';
import ListenButton from '../../components/ListenButton';
import { User, Phone, MapPin, Hash, LogOut, CheckCircle, ShieldCheck } from 'lucide-react';

interface ProfileScreenProps {
  onLogout: () => void;
}

const ProfileScreen: React.FC<ProfileScreenProps> = ({ onLogout }) => {
  const { t, language, setLanguage } = useLanguage();
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [address, setAddress] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getCustomerProfile()
      .then(data => {
        setProfile(data);
        setAddress(data.address || '');
      })
      .catch(() => {});
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    setMessage(null);
    try {
      const updated = await api.updateCustomerProfile({ address });
      setProfile(updated);
      setMessage(t('profileUpdated') || 'Profile updated successfully');
    } catch {
      setMessage('Failed to update');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-text)' }}>
          {t('profile')}
        </h2>
        <ListenButton text={`${t('profile')}, ${profile?.consumer_number || ''}`} />
      </div>

      {profile && (
        <>
          <div className="clay-card" style={{ padding: '20px', marginBottom: '16px', textAlign: 'center' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'linear-gradient(145deg, var(--color-terracotta), var(--color-terracotta-soft))',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px auto',
                boxShadow: 'inset 2px 2px 4px rgba(255,255,255,0.4), 0 4px 10px rgba(184,78,47,0.3)'
              }}
            >
              <User size={32} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-primary-text)', marginBottom: '4px' }}>
              {t('connection')}: #{profile.consumer_number}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-secondary-text)', marginBottom: '12px' }}>
              {profile.connection_type || 'DOMESTIC'} · {profile.city} - {profile.pincode}
            </p>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
              <span className="clay-badge" style={{ background: 'rgba(63,143,91,0.15)', color: 'var(--color-success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={12} /> {t('subsidy_eligible') || 'Subsidy Eligible'}
              </span>
              <span className="clay-badge" style={{ background: 'rgba(184,78,47,0.12)', color: 'var(--color-terracotta)' }}>
                {profile.cylinder_quota_limit} Quota/yr
              </span>
            </div>
          </div>

          <div className="clay-card" style={{ padding: '20px', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px', color: 'var(--color-primary-text)' }}>
              {t('contactInfo') || 'Connection Details'}
            </h4>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', fontSize: '14px', color: 'var(--color-primary-text)' }}>
              <Hash size={16} color="var(--color-terracotta)" />
              <span>Consumer: {profile.consumer_number}</span>
            </div>

            <form onSubmit={handleUpdate}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '6px' }}>
                {t('deliveryAddress') || 'Delivery Address'}
              </label>
              <div style={{ position: 'relative', marginBottom: '12px' }}>
                <textarea
                  className="clay-input"
                  rows={3}
                  value={address}
                  onChange={e => setAddress(e.target.value)}
                  style={{ width: '100%', resize: 'none', paddingLeft: '32px' }}
                />
                <MapPin size={16} color="var(--color-terracotta)" style={{ position: 'absolute', top: '12px', left: '10px' }} />
              </div>

              {message && (
                <div style={{ fontSize: '12px', color: 'var(--color-success)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle size={14} /> {message}
                </div>
              )}

              <button
                type="submit"
                className="clay-button"
                disabled={isUpdating}
                style={{ width: '100%', padding: '10px', fontSize: '14px' }}
              >
                {isUpdating ? t('loading') : (t('saveAddress') || 'Update Address')}
              </button>
            </form>
          </div>

          <div className="clay-card" style={{ padding: '16px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--color-primary-text)' }}>
                {t('language')}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-secondary-text)' }}>
                {language === 'en' ? 'English' : 'ಕನ್ನಡ'}
              </div>
            </div>
            <button
              className="clay-button-secondary"
              onClick={() => setLanguage(language === 'en' ? 'kn' : 'en')}
              style={{ padding: '8px 14px', fontSize: '13px' }}
            >
              {language === 'en' ? 'ಕನ್ನಡಕ್ಕೆ ಬದಲಿಸಿ' : 'Switch to English'}
            </button>
          </div>

          <button
            onClick={onLogout}
            className="clay-button-secondary"
            style={{
              width: '100%',
              padding: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              color: 'var(--color-error)'
            }}
          >
            <LogOut size={16} />
            <span>{t('logout') || 'Logout'}</span>
          </button>
        </>
      )}
    </div>
  );
};

export default ProfileScreen;

import React, { useEffect, useState } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { api, Booking } from '../../services/api';
import ListenButton from '../../components/ListenButton';
import { Calendar, CheckCircle2, Clock, ChevronRight } from 'lucide-react';

interface OrderHistoryProps {
  onSelectBooking: (booking: Booking) => void;
}

const OrderHistoryScreen: React.FC<OrderHistoryProps> = ({ onSelectBooking }) => {
  const { t } = useLanguage();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCustomerBookings()
      .then(res => {
        setBookings(res);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-text)' }}>
          {t('orderHistory')}
        </h2>
        <ListenButton text={t('orderHistory')} />
      </div>

      {loading ? (
        <div className="clay-card" style={{ padding: '24px', textAlign: 'center' }}>
          {t('loading')}
        </div>
      ) : bookings.length === 0 ? (
        <div className="clay-card" style={{ padding: '32px', textAlign: 'center' }}>
          <Clock size={36} color="var(--color-terracotta-soft)" style={{ marginBottom: '8px' }} />
          <p style={{ color: 'var(--color-secondary-text)', fontSize: '14px' }}>{t('noBookings')}</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {bookings.map(b => (
            <div
              key={b.id}
              className="clay-card"
              onClick={() => onSelectBooking(b)}
              style={{
                padding: '16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 800, fontSize: '15px', color: 'var(--color-primary-text)' }}>
                    #{b.booking_number}
                  </span>
                  <span
                    className="clay-badge"
                    style={{
                      background: b.status === 'DELIVERED' ? 'rgba(63,143,91,0.15)' : 'rgba(246,185,59,0.2)',
                      color: b.status === 'DELIVERED' ? 'var(--color-success)' : 'var(--color-terracotta)'
                    }}
                  >
                    {t(b.status.toLowerCase()) || b.status}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-secondary-text)' }}>
                  <Calendar size={13} />
                  <span>{new Date(b.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>{b.cylinder_type}</span>
                </div>
                <div style={{ marginTop: '8px', fontWeight: 700, fontSize: '14px', color: 'var(--color-terracotta)' }}>
                  ₹{b.total_amount}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', color: 'var(--color-terracotta)' }}>
                <ChevronRight size={20} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default OrderHistoryScreen;

import React from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { DeliveryTask } from '../../services/api';
import ListenButton from '../../components/ListenButton';
import { ArrowLeft, Phone, MapPin, Package, CheckSquare, ShieldCheck, User } from 'lucide-react';

interface DeliveryTaskDetailProps {
  task: DeliveryTask;
  onBack: () => void;
  onProceedToOutcome: (task: DeliveryTask) => void;
}

const DeliveryTaskDetailScreen: React.FC<DeliveryTaskDetailProps> = ({ task, onBack, onProceedToOutcome }) => {
  const { t } = useLanguage();

  const handleCall = () => {
    if (task.customer_phone) {
      window.location.href = `tel:${task.customer_phone}`;
    }
  };

  const handleDirections = () => {
    if (task.customer_address) {
      window.open(`https://maps.google.com/?q=${encodeURIComponent(task.customer_address)}`, '_blank');
    }
  };

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <button
          onClick={onBack}
          className="clay-button-secondary"
          style={{ padding: '8px', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <ArrowLeft size={18} color="var(--color-primary-text)" />
        </button>
        <span style={{ fontWeight: 800, fontSize: '16px', color: 'var(--color-primary-text)' }}>
          {t('taskDetails')}
        </span>
        <ListenButton text={`${task.customer_name}, ${task.customer_address}, ₹${task.total_amount}`} />
      </div>

      <div className="clay-card" style={{ padding: '20px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--color-secondary-text)', fontWeight: 600 }}>
              {t('bookingNumber')}: #{task.booking_number}
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-primary-text)' }}>
              {task.customer_name}
            </h3>
          </div>
          <span
            className="clay-badge"
            style={{
              background: task.status === 'DELIVERED' ? 'rgba(63,143,91,0.15)' : 'rgba(246,185,59,0.2)',
              color: task.status === 'DELIVERED' ? 'var(--color-success)' : 'var(--color-terracotta)'
            }}
          >
            {t(task.status.toLowerCase()) || task.status}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', fontSize: '13px', color: 'var(--color-secondary-text)' }}>
          <MapPin size={16} color="var(--color-terracotta)" />
          <span>{task.customer_address}</span>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleCall}
            className="clay-button-secondary"
            style={{ flex: 1, padding: '10px', fontSize: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
          >
            <Phone size={15} color="var(--color-terracotta)" />
            <span>{t('callCustomer')}</span>
          </button>
          <button
            onClick={handleDirections}
            className="clay-button-secondary"
            style={{ flex: 1, padding: '10px', fontSize: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
          >
            <MapPin size={15} color="var(--color-terracotta)" />
            <span>{t('getDirections')}</span>
          </button>
        </div>
      </div>

      <div className="clay-card" style={{ padding: '20px', marginBottom: '20px' }}>
        <h4 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', color: 'var(--color-primary-text)' }}>
          {t('cylinderDetails')}
        </h4>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
          <span style={{ color: 'var(--color-secondary-text)' }}>{t('cylinderType')}:</span>
          <span style={{ fontWeight: 700, color: 'var(--color-primary-text)' }}>{task.cylinder_type}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
          <span style={{ color: 'var(--color-secondary-text)' }}>{t('cylinderSerial')}:</span>
          <span style={{ fontWeight: 700, color: 'var(--color-primary-text)', fontFamily: 'monospace' }}>
            {task.cylinder_serial || 'CYL-2026-X88'}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
          <span style={{ color: 'var(--color-secondary-text)' }}>{t('paymentStatus')}:</span>
          <span style={{ fontWeight: 700, color: task.payment_status === 'PAID' ? 'var(--color-success)' : 'var(--color-terracotta)' }}>
            {task.payment_status || 'PENDING'}
          </span>
        </div>

        <div style={{ height: '1px', background: 'var(--color-terracotta-soft)', opacity: 0.3, margin: '12px 0' }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px', fontWeight: 800 }}>
          <span style={{ color: 'var(--color-primary-text)' }}>{t('collectAmount')}:</span>
          <span style={{ color: 'var(--color-terracotta)' }}>₹{task.total_amount}</span>
        </div>
      </div>

      <button
        onClick={() => onProceedToOutcome(task)}
        className="clay-button"
        style={{
          width: '100%',
          padding: '14px',
          fontSize: '15px',
          fontWeight: 800,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px'
        }}
      >
        <CheckSquare size={18} />
        <span>{t('recordOutcome')}</span>
      </button>
    </div>
  );
};

export default DeliveryTaskDetailScreen;

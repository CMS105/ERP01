import React, { useState } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { api, DeliveryTask } from '../../services/api';
import { storage } from '../../services/storage';
import ListenButton from '../../components/ListenButton';
import BluetoothPaymentModal from '../../components/BluetoothPaymentModal';
import { ArrowLeft, CheckCircle2, AlertCircle, CreditCard, Banknote, ShieldAlert, WifiOff } from 'lucide-react';

interface DeliveryOutcomeProps {
  task: DeliveryTask;
  onBack: () => void;
  onSuccess: () => void;
}

const DeliveryOutcomeScreen: React.FC<DeliveryOutcomeProps> = ({ task, onBack, onSuccess }) => {
  const { t } = useLanguage();
  const [outcome, setOutcome] = useState('DELIVERED_SUCCESS');
  const [emptySerial, setEmptySerial] = useState('CYL-EMPTY-' + Math.floor(1000 + Math.random() * 9000));
  const [paymentMethod, setPaymentMethod] = useState<'CASH' | 'ONLINE' | 'MPOS'>('CASH');
  const [showBluetoothModal, setShowBluetoothModal] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(task.payment_status === 'PAID');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [completedInfo, setCompletedInfo] = useState<{ isOffline: boolean; id: string } | null>(null);

  const outcomes = [
    { id: 'DELIVERED_SUCCESS', label: t('outcomeDelivered') },
    { id: 'CUSTOMER_UNAVAILABLE', label: t('outcomeCustomerUnavailable') },
    { id: 'ADDRESS_NOT_FOUND', label: t('outcomeAddressNotFound') },
    { id: 'CYLINDER_DEFECTIVE', label: t('outcomeDefective') },
    { id: 'RESCHEDULED', label: t('outcomeRescheduled') }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const payload = {
      outcome,
      empty_cylinder_serial: outcome === 'DELIVERED_SUCCESS' ? emptySerial : undefined,
      notes,
      payment_method: paymentMethod,
      payment_collected: outcome === 'DELIVERED_SUCCESS' ? task.total_amount : 0
    };

    try {
      if (!navigator.onLine) {
        throw new Error('Offline');
      }
      await api.recordDeliveryOutcome(task.id, payload);
      setCompletedInfo({ isOffline: false, id: String(task.id) });
    } catch {
      const offlineId = storage.queueDeliveryOutcome(task.id, payload);
      setCompletedInfo({ isOffline: true, id: offlineId });
    } finally {
      setIsSubmitting(false);
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
          {t('recordOutcome')}
        </span>
        <ListenButton text={`${t('recordOutcome')} ${task.customer_name}`} />
      </div>

      {completedInfo ? (
        <div className="clay-card" style={{ padding: '24px', textAlign: 'center' }}>
          <div
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '50%',
              background: completedInfo.isOffline ? 'rgba(246,185,59,0.2)' : 'rgba(63,143,91,0.2)',
              color: completedInfo.isOffline ? 'var(--color-marigold)' : 'var(--color-success)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto'
            }}
          >
            {completedInfo.isOffline ? <WifiOff size={32} /> : <CheckCircle2 size={32} />}
          </div>

          <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-primary-text)', marginBottom: '8px' }}>
            {completedInfo.isOffline ? t('savedOffline') : t('outcomeRecorded')}
          </h3>

          <p style={{ fontSize: '13px', color: 'var(--color-secondary-text)', marginBottom: '16px' }}>
            {completedInfo.isOffline ? t('savedOfflineDesc') : t('outcomeSuccessDesc')}
          </p>

          <div style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--color-terracotta)', marginBottom: '20px' }}>
            ID: {completedInfo.id}
          </div>

          <button
            onClick={onSuccess}
            className="clay-button"
            style={{ width: '100%', padding: '12px' }}
          >
            {t('backToTasks')}
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="clay-card" style={{ padding: '18px', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px', color: 'var(--color-primary-text)' }}>
              {t('selectOutcome')}
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {outcomes.map(item => (
                <label
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 12px',
                    borderRadius: '12px',
                    background: outcome === item.id ? 'var(--color-cream-dark)' : 'transparent',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: outcome === item.id ? 700 : 500,
                    color: 'var(--color-primary-text)'
                  }}
                >
                  <input
                    type="radio"
                    name="outcome"
                    value={item.id}
                    checked={outcome === item.id}
                    onChange={e => setOutcome(e.target.value)}
                    style={{ accentColor: 'var(--color-terracotta)' }}
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
          </div>

          {outcome === 'DELIVERED_SUCCESS' && (
            <>
              <div className="clay-card" style={{ padding: '18px', marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '6px' }}>
                  {t('emptyCylinderSerial')}
                </label>
                <input
                  type="text"
                  className="clay-input"
                  value={emptySerial}
                  onChange={e => setEmptySerial(e.target.value)}
                  style={{ width: '100%', fontFamily: 'monospace', fontSize: '14px', fontWeight: 700 }}
                  required
                />
              </div>

              <div className="clay-card" style={{ padding: '18px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-text)' }}>
                    {t('paymentCollection')} (₹{task.total_amount})
                  </h4>
                  {paymentSuccess && (
                    <span className="clay-badge" style={{ background: 'rgba(63,143,91,0.15)', color: 'var(--color-success)' }}>
                      {t('paid')}
                    </span>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('CASH')}
                    className="clay-badge"
                    style={{
                      border: 'none',
                      padding: '10px 4px',
                      cursor: 'pointer',
                      background: paymentMethod === 'CASH' ? 'var(--color-terracotta)' : 'var(--color-cream)',
                      color: paymentMethod === 'CASH' ? '#fff' : 'var(--color-primary-text)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Banknote size={16} />
                    <span>{t('cash')}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod('ONLINE')}
                    className="clay-badge"
                    style={{
                      border: 'none',
                      padding: '10px 4px',
                      cursor: 'pointer',
                      background: paymentMethod === 'ONLINE' ? 'var(--color-terracotta)' : 'var(--color-cream)',
                      color: paymentMethod === 'ONLINE' ? '#fff' : 'var(--color-primary-text)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <CreditCard size={16} />
                    <span>UPI / QR</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setPaymentMethod('MPOS');
                      setShowBluetoothModal(true);
                    }}
                    className="clay-badge"
                    style={{
                      border: 'none',
                      padding: '10px 4px',
                      cursor: 'pointer',
                      background: paymentMethod === 'MPOS' ? 'var(--color-terracotta)' : 'var(--color-cream)',
                      color: paymentMethod === 'MPOS' ? '#fff' : 'var(--color-primary-text)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <CreditCard size={16} />
                    <span>{t('mposCard')}</span>
                  </button>
                </div>

                {paymentMethod === 'MPOS' && !paymentSuccess && (
                  <button
                    type="button"
                    onClick={() => setShowBluetoothModal(true)}
                    className="clay-button-secondary"
                    style={{ width: '100%', padding: '8px', fontSize: '12px' }}
                  >
                    {t('launchBluetoothTerminal')}
                  </button>
                )}
              </div>
            </>
          )}

          <div className="clay-card" style={{ padding: '18px', marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary-text)', marginBottom: '6px' }}>
              {t('remarksOrNotes')}
            </label>
            <textarea
              className="clay-input"
              rows={2}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder={t('optionalRemarks')}
              style={{ width: '100%', resize: 'none' }}
            />
          </div>

          <button
            type="submit"
            className="clay-button"
            disabled={isSubmitting}
            style={{ width: '100%', padding: '14px', fontSize: '15px', fontWeight: 800 }}
          >
            {isSubmitting ? t('submitting') : t('submitOutcome')}
          </button>
        </form>
      )}

      {showBluetoothModal && (
        <BluetoothPaymentModal
          amount={task.total_amount || 650}
          onSuccess={() => {
            setPaymentSuccess(true);
            setShowBluetoothModal(false);
          }}
          onClose={() => setShowBluetoothModal(false)}
        />
      )}
    </div>
  );
};

export default DeliveryOutcomeScreen;

import React, { useEffect, useState } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { api, DeliveryTask } from '../../services/api';
import { storage } from '../../services/storage';
import ListenButton from '../../components/ListenButton';
import { Package, CheckCircle2, Clock, MapPin, RefreshCw, ChevronRight, Search } from 'lucide-react';

interface DeliveryTaskListProps {
  onSelectTask: (task: DeliveryTask) => void;
  onRefreshOffline: () => void;
}

const DeliveryTaskListScreen: React.FC<DeliveryTaskListProps> = ({ onSelectTask, onRefreshOffline }) => {
  const { t } = useLanguage();
  const [tasks, setTasks] = useState<DeliveryTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'ALL' | 'ASSIGNED' | 'DELIVERED'>('ALL');
  const [isSyncing, setIsSyncing] = useState(false);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await api.getDeliveryTasks();
      setTasks(data);
      storage.cacheDeliveryTasks(data);
    } catch {
      setTasks(storage.getCachedDeliveryTasks());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const handleSync = async () => {
    setIsSyncing(true);
    await storage.syncQueuedOutcomes();
    onRefreshOffline();
    await loadTasks();
    setIsSyncing(false);
  };

  const pendingCount = tasks.filter(t => t.status === 'ASSIGNED' || t.status === 'OUT_FOR_DELIVERY').length;
  const completedCount = tasks.filter(t => t.status === 'DELIVERED').length;

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
      task.customer_address?.toLowerCase().includes(search.toLowerCase()) ||
      task.booking_number?.toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;
    if (filter === 'ASSIGNED') return task.status === 'ASSIGNED' || task.status === 'OUT_FOR_DELIVERY';
    if (filter === 'DELIVERED') return task.status === 'DELIVERED';
    return true;
  });

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-text)' }}>
            {t('deliveryPartner')}
          </h2>
          <span style={{ fontSize: '13px', color: 'var(--color-secondary-text)' }}>
            {t('todaySummary')}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="clay-button-secondary"
            style={{ padding: '6px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
            <span>{t('sync')}</span>
          </button>
          <ListenButton text={`${t('assigned')}: ${pendingCount}, ${t('delivered')}: ${completedCount}`} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
        <div className="clay-card" style={{ padding: '12px', textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-terracotta)' }}>{tasks.length}</div>
          <div style={{ fontSize: '11px', color: 'var(--color-secondary-text)', fontWeight: 600 }}>{t('total')}</div>
        </div>
        <div className="clay-card" style={{ padding: '12px', textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-marigold)' }}>{pendingCount}</div>
          <div style={{ fontSize: '11px', color: 'var(--color-secondary-text)', fontWeight: 600 }}>{t('assigned')}</div>
        </div>
        <div className="clay-card" style={{ padding: '12px', textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-success)' }}>{completedCount}</div>
          <div style={{ fontSize: '11px', color: 'var(--color-secondary-text)', fontWeight: 600 }}>{t('delivered')}</div>
        </div>
      </div>

      <div style={{ position: 'relative', marginBottom: '12px' }}>
        <input
          type="text"
          className="clay-input"
          placeholder={t('searchTaskPlaceholder')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: '100%', paddingLeft: '34px', fontSize: '13px' }}
        />
        <Search size={16} color="var(--color-secondary-text)" style={{ position: 'absolute', top: '12px', left: '10px' }} />
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {(['ALL', 'ASSIGNED', 'DELIVERED'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className="clay-badge"
            style={{
              cursor: 'pointer',
              border: 'none',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 700,
              background: filter === tab ? 'var(--color-terracotta)' : 'var(--color-cream)',
              color: filter === tab ? '#fff' : 'var(--color-primary-text)',
              boxShadow: filter === tab ? 'var(--shadow-clay-primary)' : 'var(--shadow-clay-card)'
            }}
          >
            {tab === 'ALL' ? t('all') : tab === 'ASSIGNED' ? t('assigned') : t('delivered')}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="clay-card" style={{ padding: '24px', textAlign: 'center' }}>
          {t('loading')}
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="clay-card" style={{ padding: '32px', textAlign: 'center' }}>
          <Package size={36} color="var(--color-terracotta-soft)" style={{ marginBottom: '8px' }} />
          <p style={{ color: 'var(--color-secondary-text)', fontSize: '14px' }}>{t('noTasksFound')}</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredTasks.map(task => (
            <div
              key={task.id}
              className="clay-card"
              onClick={() => onSelectTask(task)}
              style={{
                padding: '16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderLeft: task.status === 'DELIVERED' ? '4px solid var(--color-success)' : '4px solid var(--color-terracotta)'
              }}
            >
              <div style={{ flex: 1, paddingRight: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 800, fontSize: '15px', color: 'var(--color-primary-text)' }}>
                    {task.customer_name}
                  </span>
                  <span
                    className="clay-badge"
                    style={{
                      fontSize: '10px',
                      background: task.status === 'DELIVERED' ? 'rgba(63,143,91,0.15)' : 'rgba(246,185,59,0.2)',
                      color: task.status === 'DELIVERED' ? 'var(--color-success)' : 'var(--color-terracotta)'
                    }}
                  >
                    {t(task.status.toLowerCase()) || task.status}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--color-secondary-text)', marginBottom: '6px' }}>
                  <MapPin size={13} color="var(--color-terracotta)" />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '200px' }}>
                    {task.customer_address}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '10px', fontSize: '11px', color: 'var(--color-primary-text)', fontWeight: 600 }}>
                  <span>#{task.booking_number}</span>
                  <span>•</span>
                  <span>₹{task.total_amount} ({task.payment_status || 'PENDING'})</span>
                </div>
              </div>

              <ChevronRight size={20} color="var(--color-terracotta)" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DeliveryTaskListScreen;

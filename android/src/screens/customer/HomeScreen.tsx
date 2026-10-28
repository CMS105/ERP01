import React, { useState, useEffect } from "react";
import { Flame, Calendar, CheckCircle2, ChevronRight, PackageCheck, AlertCircle, ShoppingBag } from "lucide-react";
import { api, CustomerProfile, Booking } from "../../services/api";
import { useLanguage } from "../../i18n/LanguageContext";
import { ListenButton } from "../../components/ListenButton";

export interface CustomerHomeScreenProps {
  onNavigateToBooking: () => void;
  onNavigateToHistory: () => void;
  onSelectBooking: (booking: Booking) => void;
}

export const CustomerHomeScreen: React.FC<CustomerHomeScreenProps> = ({
  onNavigateToBooking,
  onNavigateToHistory,
  onSelectBooking
}) => {
  const { t } = useLanguage();
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [activeBooking, setActiveBooking] = useState<Booking | null>(null);
  const [recentBookings, setRecentBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [profData, bookingsData] = await Promise.all([
        api.getCustomerProfile(),
        api.getCustomerBookings()
      ]);
      setProfile(profData);
      setRecentBookings(bookingsData.slice(0, 3));
      const inProgress = bookingsData.find(
        (b) => b.status === "PENDING" || b.status === "ASSIGNED" || b.status === "OUT_FOR_DELIVERY"
      );
      setActiveBooking(inProgress || null);
    } catch (err: any) {
      setError(err.message || "Failed to load customer profile");
    } finally {
      setLoading(false);
    }
  };

  const remainingQuota = profile ? Math.max(0, profile.cylinder_quota_limit - profile.quota_used_this_year) : 0;

  if (loading) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)" }}>
        <p>{t("loading")}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
      {error && (
        <div className="clay-card" style={{ background: "var(--error-bg)", border: "1px solid var(--error)", color: "var(--error)", padding: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertCircle size={18} />
            <span style={{ fontSize: "13px", fontWeight: "600" }}>{error}</span>
          </div>
        </div>
      )}

      <div className="clay-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div>
            <h2 style={{ fontSize: "18px", fontWeight: "800", color: "var(--primary-terracotta)", margin: 0 }}>
              {t("quota_balance")}
            </h2>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {t("consumer_no")}: <b>{profile?.consumer_number || "..."}</b>
            </span>
          </div>
          <ListenButton text={`${t("quota_balance")}: ${remainingQuota} ${t("remaining")}`} />
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginBottom: "8px" }}>
          <span style={{ fontSize: "36px", fontWeight: "800", color: "var(--primary-terracotta)" }}>
            {remainingQuota}
          </span>
          <span style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-main)" }}>
            / {profile?.cylinder_quota_limit || 12}
          </span>
          <span style={{ fontSize: "13px", color: "var(--text-muted)", marginLeft: "4px" }}>
            {t("cylinders_per_year")}
          </span>
        </div>

        <div className="quota-bar" style={{ marginBottom: "12px" }}>
          <div
            className="quota-progress"
            style={{
              width: `${Math.min(100, ((profile?.quota_used_this_year || 0) / (profile?.cylinder_quota_limit || 12)) * 100)}%`
            }}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)" }}>
          <span>{t("used")}: <b>{profile?.quota_used_this_year || 0}</b></span>
          <span className="clay-badge success" style={{ fontSize: "11px" }}>{t("subsidy_eligible")}</span>
        </div>
      </div>

      <button
        className="clay-button-primary"
        onClick={onNavigateToBooking}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          padding: "16px",
          fontSize: "16px"
        }}
      >
        <ShoppingBag size={20} />
        <span>{t("book_cylinder_now")}</span>
      </button>

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", padding: "0 4px" }}>
          <h2 style={{ fontSize: "14px", fontWeight: "800", margin: 0 }}>{t("active_order")}</h2>
          {activeBooking && (
            <ListenButton text={`${t("active_order")} ${activeBooking.booking_number}, ${activeBooking.status}`} />
          )}
        </div>

        {activeBooking ? (
          <div
            className="clay-card"
            style={{ cursor: "pointer", borderLeft: "4px solid var(--primary-terracotta)" }}
            onClick={() => onSelectBooking(activeBooking)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
              <div>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "700" }}>
                  {activeBooking.cylinder_type}
                </span>
                <div style={{ fontSize: "16px", fontWeight: "800", color: "var(--text-main)" }}>
                  {activeBooking.booking_number}
                </div>
              </div>
              <span className={`clay-badge ${activeBooking.status === "DELIVERED" ? "success" : "info"}`}>
                {activeBooking.status}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-muted)", marginBottom: "10px" }}>
              <Calendar size={13} color="var(--primary-terracotta)" />
              <span>{t("scheduled_for")}: <b>{activeBooking.scheduled_date}</b></span>
            </div>

            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              paddingTop: "8px",
              borderTop: "1px dashed var(--card-border)",
              fontSize: "12px"
            }}>
              <div>
                <span style={{ color: "var(--text-muted)" }}>{t("net_payable")}: </span>
                <b style={{ color: "var(--primary-terracotta)", fontSize: "14px" }}>₹{activeBooking.net_payable}</b>
              </div>
              <span style={{ display: "flex", alignItems: "center", gap: "2px", color: "var(--primary-terracotta)", fontWeight: "700" }}>
                {t("track_order")} <ChevronRight size={14} />
              </span>
            </div>
          </div>
        ) : (
          <div className="clay-card" style={{ textAlign: "center", padding: "24px 16px", color: "var(--text-muted)" }}>
            <PackageCheck size={32} color="var(--soft-terracotta)" style={{ margin: "0 auto 8px" }} />
            <p style={{ fontSize: "13px", fontWeight: "600" }}>{t("no_active_booking")}</p>
          </div>
        )}
      </div>

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", padding: "0 4px" }}>
          <h2 style={{ fontSize: "14px", fontWeight: "800", margin: 0 }}>{t("recent_orders")}</h2>
          <button
            onClick={onNavigateToHistory}
            style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary-terracotta)", background: "none", border: "none", cursor: "pointer" }}
          >
            View All
          </button>
        </div>

        {recentBookings.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {recentBookings.map((b) => (
              <div
                key={b.id}
                className="clay-card-flat"
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
                onClick={() => onSelectBooking(b)}
              >
                <div>
                  <div style={{ fontWeight: "700", fontSize: "13px" }}>{b.booking_number}</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {b.scheduled_date} · ₹{b.net_payable}
                  </div>
                </div>
                <span className={`clay-badge ${b.status === "DELIVERED" ? "success" : "info"}`}>
                  {b.status}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="clay-card-flat" style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>
            {t("no_history")}
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerHomeScreen;

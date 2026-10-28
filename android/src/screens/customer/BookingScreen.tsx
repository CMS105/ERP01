import React, { useState } from "react";
import { ArrowLeft, CheckCircle2, AlertTriangle, ShieldCheck, Calendar, Package } from "lucide-react";
import { api, Booking } from "../../services/api";
import { useLanguage } from "../../i18n/LanguageContext";
import { ListenButton } from "../../components/ListenButton";

interface BookingScreenProps {
  onBack: () => void;
  onBookingSuccess: (booking: Booking) => void;
}

export const BookingScreen: React.FC<BookingScreenProps> = ({ onBack, onBookingSuccess }) => {
  const { t } = useLanguage();
  const [cylinderType, setCylinderType] = useState("14.2kg");
  const [quantity, setQuantity] = useState(1);
  const [scheduledDate, setScheduledDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 2);
    return d.toISOString().split("T")[0];
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdBooking, setCreatedBooking] = useState<Booking | null>(null);

  const basePrice = 850.0 * quantity;
  const subsidyAmount = 200.0 * quantity;
  const netPayable = basePrice - subsidyAmount;

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.createBooking({
        cylinder_type: cylinderType,
        quantity,
        scheduled_date: scheduledDate
      });
      setCreatedBooking(res);
      onBookingSuccess(res);
    } catch (err: any) {
      setError(err.message || t("booking_failed"));
    } finally {
      setLoading(false);
    }
  };

  if (createdBooking) {
    return (
      <div style={{ padding: "20px 16px", textAlign: "center" }}>
        <div className="clay-card" style={{ padding: "30px 20px" }}>
          <CheckCircle2 size={54} color="var(--success)" style={{ margin: "0 auto 14px" }} />
          <h2 style={{ fontSize: "18px", fontWeight: "800", color: "var(--success)" }}>
            {t("booking_success_title")}
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "6px" }}>
            {t("booking_success_desc")} <b>{createdBooking.booking_number}</b>
          </p>

          <div style={{
            background: "var(--bg-cream)",
            padding: "14px",
            borderRadius: "var(--radius-md)",
            margin: "20px 0",
            textAlign: "left",
            fontSize: "12px",
            display: "flex",
            flexDirection: "column",
            gap: "6px"
          }}>
            <div>{t("select_cylinder_type")}: <b>{createdBooking.cylinder_type}</b></div>
            <div>{t("delivery_date")}: <b>{createdBooking.scheduled_date}</b></div>
            <div>{t("net_payable")}: <b style={{ color: "var(--primary-terracotta)", fontSize: "14px" }}>₹{createdBooking.net_payable}</b></div>
          </div>

          <button className="clay-button-primary" style={{ width: "100%" }} onClick={onBack}>
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <button
          onClick={onBack}
          style={{
            padding: "8px",
            borderRadius: "50%",
            background: "var(--card-bg)",
            boxShadow: "var(--clay-shadow-sm)"
          }}
        >
          <ArrowLeft size={18} />
        </button>
        <h2 style={{ fontSize: "16px", fontWeight: "800", margin: 0 }}>
          {t("book_cylinder")}
        </h2>
        <ListenButton text={`${t("book_cylinder")}. ${t("price_details")}. ${t("net_payable")} ₹${netPayable}`} />
      </div>

      {error && (
        <div style={{
          padding: "12px 14px",
          background: "var(--error-bg)",
          color: "var(--error)",
          borderRadius: "var(--radius-md)",
          fontSize: "13px",
          display: "flex",
          alignItems: "center",
          gap: "8px"
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="clay-card">
        <label style={{ fontSize: "13px", fontWeight: "700", marginBottom: "8px", display: "block" }}>
          {t("select_cylinder_type")}
        </label>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={() => setCylinderType("14.2kg")}
            style={{
              flex: 1,
              padding: "14px 10px",
              borderRadius: "var(--radius-md)",
              border: `2px solid ${cylinderType === "14.2kg" ? "var(--primary-terracotta)" : "var(--card-border)"}`,
              background: cylinderType === "14.2kg" ? "var(--bg-cream)" : "var(--card-bg)",
              fontWeight: "700",
              fontSize: "12px",
              textAlign: "center"
            }}
          >
            <Package size={20} color="var(--primary-terracotta)" style={{ margin: "0 auto 4px" }} />
            <div>14.2kg Domestic</div>
            <div style={{ fontSize: "10px", color: "var(--success)" }}>Subsidized</div>
          </button>

          <button
            type="button"
            onClick={() => setCylinderType("19kg")}
            style={{
              flex: 1,
              padding: "14px 10px",
              borderRadius: "var(--radius-md)",
              border: `2px solid ${cylinderType === "19kg" ? "var(--primary-terracotta)" : "var(--card-border)"}`,
              background: cylinderType === "19kg" ? "var(--bg-cream)" : "var(--card-bg)",
              fontWeight: "700",
              fontSize: "12px",
              textAlign: "center"
            }}
          >
            <Package size={20} color="var(--text-muted)" style={{ margin: "0 auto 4px" }} />
            <div>19kg Commercial</div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Commercial</div>
          </button>
        </div>
      </div>

      <div className="clay-card">
        <label style={{ fontSize: "13px", fontWeight: "700", marginBottom: "8px", display: "block" }}>
          {t("delivery_date")}
        </label>
        <input
          type="date"
          value={scheduledDate}
          min={new Date().toISOString().split("T")[0]}
          onChange={(e) => setScheduledDate(e.target.value)}
        />
      </div>

      <div className="clay-card">
        <h3 style={{ fontSize: "14px", fontWeight: "800", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
          <ShieldCheck size={16} color="var(--primary-terracotta)" />
          {t("price_details")}
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "var(--text-muted)" }}>{t("base_price")}</span>
            <span>₹{basePrice.toFixed(2)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--success)" }}>
            <span>{t("subsidy_amount")}</span>
            <span>- ₹{subsidyAmount.toFixed(2)}</span>
          </div>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            paddingTop: "10px",
            borderTop: "1px dashed var(--card-border)",
            fontWeight: "800",
            fontSize: "15px"
          }}>
            <span>{t("net_payable")}</span>
            <span style={{ color: "var(--primary-terracotta)", fontSize: "17px" }}>₹{netPayable.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <button
        className="clay-button-primary"
        onClick={handleConfirm}
        disabled={loading}
      >
        <span>{loading ? "Confirming with Server..." : t("confirm_booking")}</span>
      </button>
    </div>
  );
};

export default BookingScreen;

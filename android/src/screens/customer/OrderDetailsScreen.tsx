import React, { useState } from "react";
import { ArrowLeft, CheckCircle2, Clock, Truck, MapPin, Phone, CreditCard, ShieldCheck } from "lucide-react";
import { Booking } from "../../services/api";
import { useLanguage } from "../../i18n/LanguageContext";
import { BluetoothPaymentModal } from "../../components/BluetoothPaymentModal";

interface OrderDetailsScreenProps {
  booking: Booking;
  onBack: () => void;
}

export const OrderDetailsScreen: React.FC<OrderDetailsScreenProps> = ({ booking, onBack }) => {
  const { t } = useLanguage();
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentDone, setPaymentDone] = useState(booking.status === "DELIVERED");

  const steps = [
    { title: t("order_placed"), done: true },
    { title: t("assigned"), done: booking.status !== "PENDING" },
    { title: t("out_for_delivery"), done: booking.status === "OUT_FOR_DELIVERY" || booking.status === "DELIVERED" },
    { title: t("delivered"), done: booking.status === "DELIVERED" }
  ];

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
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: "800", margin: 0 }}>
            {t("booking_details")}
          </h2>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{booking.booking_number}</span>
        </div>
      </div>

      <div className="clay-card">
        <h3 style={{ fontSize: "14px", fontWeight: "700", marginBottom: "14px" }}>
          {t("track_order")}
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px", position: "relative" }}>
          {steps.map((step, idx) => (
            <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "12px", position: "relative" }}>
              <div style={{
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                background: step.done ? "var(--success)" : "var(--bg-cream-dark)",
                color: step.done ? "#FFF" : "var(--text-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "12px",
                fontWeight: "700",
                zIndex: 2
              }}>
                {step.done ? <CheckCircle2 size={16} /> : idx + 1}
              </div>
              <div>
                <div style={{ fontSize: "13px", fontWeight: step.done ? "700" : "500", color: step.done ? "var(--text-main)" : "var(--text-light)" }}>
                  {step.title}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="clay-card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>{t("driver_info")}</span>
          <b style={{ fontSize: "14px" }}>Amit Singh</b>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Vehicle: <b>KA-01-AB-1234</b>
          </div>
        </div>
        <a
          href="tel:9876543212"
          className="clay-button-secondary"
          style={{ minHeight: "40px", padding: "8px 14px", color: "var(--primary-terracotta)", textDecoration: "none" }}
        >
          <Phone size={14} />
          <span>{t("call")}</span>
        </a>
      </div>

      <div className="clay-card" style={{ textAlign: "center", padding: "20px" }}>
        <MapPin size={28} color="var(--primary-terracotta)" style={{ margin: "0 auto 6px" }} />
        <h4 style={{ fontSize: "13px", fontWeight: "700" }}>{t("map_placeholder")}</h4>
        <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
          Delivery Hub Central Route · Estimated window 2:00 PM - 5:00 PM
        </p>
      </div>

      <div className="clay-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{t("net_payable")}</span>
            <div style={{ fontSize: "20px", fontWeight: "800", color: "var(--primary-terracotta)" }}>
              ₹{booking.net_payable}
            </div>
          </div>
          <span className={`clay-badge ${paymentDone ? "success" : "warning"}`}>
            {paymentDone ? "PAID" : "PAYMENT PENDING"}
          </span>
        </div>

        {!paymentDone && (
          <button
            className="clay-button-primary"
            style={{ width: "100%" }}
            onClick={() => setShowPaymentModal(true)}
          >
            <CreditCard size={18} />
            <span>{t("pay_now")}</span>
          </button>
        )}
      </div>

      <BluetoothPaymentModal
        isOpen={showPaymentModal}
        amount={booking.net_payable}
        onClose={() => setShowPaymentModal(false)}
        onSuccess={() => {
          setShowPaymentModal(false);
          setPaymentDone(true);
        }}
      />
    </div>
  );
};

export default OrderDetailsScreen;

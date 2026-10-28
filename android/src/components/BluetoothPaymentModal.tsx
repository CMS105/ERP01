import React, { useState, useEffect } from "react";
import { Bluetooth, CheckCircle2, AlertCircle, RefreshCw, X, ShieldAlert } from "lucide-react";
import { BluetoothState, mockBluetooth } from "../services/mockBluetooth";
import { useLanguage } from "../i18n/LanguageContext";

export interface BluetoothPaymentModalProps {
  isOpen?: boolean;
  amount: number;
  onClose: () => void;
  onSuccess: () => void;
}

export const BluetoothPaymentModal: React.FC<BluetoothPaymentModalProps> = ({
  isOpen = true,
  amount,
  onClose,
  onSuccess
}) => {
  const { t } = useLanguage();
  const [state, setState] = useState<BluetoothState>("idle");

  useEffect(() => {
    if (isOpen) {
      mockBluetooth.subscribe((newState) => {
        setState(newState);
        if (newState === "success") {
          setTimeout(() => {
            onSuccess();
          }, 1500);
        }
      });
      mockBluetooth.startPaymentProcess(amount, false);
    } else {
      mockBluetooth.cancel();
      setState("idle");
    }
  }, [isOpen, amount]);

  if (!isOpen) return null;

  const renderStateContent = () => {
    switch (state) {
      case "scanning":
        return (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <RefreshCw size={36} className="animate-spin" color="var(--color-terracotta, #B84E2F)" style={{ margin: "0 auto 12px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: "700" }}>{t("bt_scanning") || "Scanning"}</h3>
            <p style={{ fontSize: "12px", color: "var(--color-secondary-text, #7A5C43)", marginTop: "4px" }}>Searching for mPOS reader...</p>
          </div>
        );
      case "deviceFound":
      case "connecting":
        return (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <Bluetooth size={36} color="var(--color-terracotta, #B84E2F)" style={{ margin: "0 auto 12px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: "700" }}>{t("bt_found") || "Device Found"}</h3>
            <p style={{ fontSize: "12px", color: "var(--color-secondary-text, #7A5C43)", marginTop: "4px" }}>Connecting securely to mPOS Terminal #8821...</p>
          </div>
        );
      case "confirmAmount":
      case "processing":
        return (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: "32px", fontWeight: "800", color: "var(--color-terracotta, #B84E2F)", marginBottom: "4px" }}>
              ₹{amount.toFixed(2)}
            </div>
            <p style={{ fontSize: "13px", fontWeight: "600", color: "var(--color-primary-text, #3A2618)" }}>Tap NFC Card or Scan QR on Terminal</p>
            <p style={{ fontSize: "12px", color: "var(--color-secondary-text, #7A5C43)", marginTop: "6px" }}>{t("bt_processing") || "Processing"}</p>
          </div>
        );
      case "success":
        return (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <CheckCircle2 size={44} color="var(--color-success, #3F8F5B)" style={{ margin: "0 auto 12px" }} />
            <h3 style={{ fontSize: "17px", fontWeight: "800", color: "var(--color-success, #3F8F5B)" }}>{t("bt_success") || "Success"}</h3>
            <p style={{ fontSize: "12px", color: "var(--color-secondary-text, #7A5C43)", marginTop: "4px" }}>Ref: TXN-BT-DEMO-{Math.floor(100000 + Math.random() * 900000)}</p>
          </div>
        );
      case "failed":
      case "timeout":
        return (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <AlertCircle size={44} color="var(--color-error, #C0392B)" style={{ margin: "0 auto 12px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: "700", color: "var(--color-error, #C0392B)" }}>{t("bt_failed") || "Failed"}</h3>
            <p style={{ fontSize: "12px", color: "var(--color-secondary-text, #7A5C43)", marginTop: "4px" }}>Please verify terminal Bluetooth pairing and retry.</p>
            <button
              className="clay-button"
              style={{ marginTop: "16px", width: "100%" }}
              onClick={() => mockBluetooth.startPaymentProcess(amount, false)}
            >
              {t("retry") || "Retry"}
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(58, 38, 24, 0.45)",
      backdropFilter: "blur(4px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
      zIndex: 100
    }}>
      <div className="clay-card" style={{ width: "100%", maxWidth: "380px", position: "relative" }}>
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: "14px",
            right: "14px",
            padding: "4px",
            borderRadius: "50%",
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--color-secondary-text, #7A5C43)"
          }}
        >
          <X size={18} />
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <Bluetooth size={18} color="var(--color-terracotta, #B84E2F)" />
          <h2 style={{ fontSize: "16px", fontWeight: "800", margin: 0 }}>{t("payment_title") || "Payment"}</h2>
        </div>

        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "6px 10px",
          borderRadius: "8px",
          background: "rgba(246,185,59,0.2)",
          color: "var(--color-terracotta, #B84E2F)",
          fontSize: "11px",
          fontWeight: "600",
          marginBottom: "12px"
        }}>
          <ShieldAlert size={14} />
          <span>{t("demo_mock_label") || "SIMULATED mPOS TERMINAL (DEMO)"}</span>
        </div>

        {renderStateContent()}
      </div>
    </div>
  );
};

export default BluetoothPaymentModal;

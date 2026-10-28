import React from "react";
import { Flame, Globe, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

export interface HeaderProps {
  role: "CUSTOMER" | "DELIVERY_BOY";
  onSwitchRole: () => void;
  isOnline?: boolean;
  offlinePendingCount?: number;
  pendingSyncCount?: number;
  onSyncNow?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  role,
  onSwitchRole,
  isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true,
  offlinePendingCount = 0,
  pendingSyncCount = 0,
  onSyncNow
}) => {
  const { language, setLanguage, t } = useLanguage();
  const count = offlinePendingCount || pendingSyncCount;

  const toggleLanguage = () => {
    setLanguage(language === "en" ? "kn" : "en");
  };

  return (
    <header style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "14px 18px",
      background: "var(--card-bg, #F3E2CF)",
      borderBottom: "1px solid var(--card-border, rgba(184, 78, 47, 0.15))",
      position: "sticky",
      top: 0,
      zIndex: 40
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div style={{
          width: "36px",
          height: "36px",
          borderRadius: "10px",
          background: "linear-gradient(135deg, var(--primary-terracotta, #B84E2F), var(--color-marigold, #F6B93B))",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#FFF",
          boxShadow: "var(--clay-shadow-sm, 2px 2px 5px rgba(0,0,0,0.1))"
        }}>
          <Flame size={20} />
        </div>
        <div>
          <h1 style={{ fontSize: "16px", fontWeight: "800", color: "var(--primary-terracotta, #B84E2F)", lineHeight: 1.1 }}>
            {t("app_title") || "LPG Suvidha"}
          </h1>
          <span style={{ fontSize: "11px", color: "var(--text-muted, #7A5C43)", fontWeight: "600" }}>
            {role === "CUSTOMER" ? (t("role_customer") || "Customer") : (t("role_delivery") || "Delivery Partner")}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          fontSize: "11px",
          fontWeight: "700",
          padding: "4px 8px",
          borderRadius: "20px",
          background: isOnline ? "rgba(63,143,91,0.15)" : "rgba(246,185,59,0.2)",
          color: isOnline ? "var(--color-success, #3F8F5B)" : "var(--color-terracotta, #B84E2F)",
          border: `1px solid ${isOnline ? "rgba(63,143,91,0.2)" : "rgba(211,84,0,0.2)"}`
        }}>
          {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
          <span>{isOnline ? (t("online") || "Online") : (t("offline") || "Offline")}</span>
          {count > 0 && (
            <span
              onClick={onSyncNow}
              style={{
                marginLeft: "2px",
                padding: "1px 5px",
                background: "var(--color-terracotta, #B84E2F)",
                color: "#FFF",
                borderRadius: "10px",
                cursor: "pointer"
              }}
              title="Click to sync now"
            >
              {count} <RefreshCw size={9} style={{ display: "inline" }} />
            </span>
          )}
        </div>

        <button
          onClick={toggleLanguage}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            padding: "5px 10px",
            borderRadius: "12px",
            background: "var(--color-cream, #FBF1E3)",
            border: "1px solid rgba(184, 78, 47, 0.2)",
            fontSize: "12px",
            fontWeight: "700",
            color: "var(--color-primary-text, #3A2618)",
            cursor: "pointer"
          }}
          aria-label={t("language")}
        >
          <Globe size={13} color="var(--color-terracotta, #B84E2F)" />
          <span>{language === "en" ? "ಕನ್ನಡ" : "ENG"}</span>
        </button>

        <button
          onClick={onSwitchRole}
          style={{
            padding: "5px 10px",
            borderRadius: "12px",
            background: "var(--color-cream-dark, #F3E2CF)",
            border: "1px solid rgba(184,78,47,0.2)",
            fontSize: "11px",
            fontWeight: "700",
            color: "var(--color-terracotta, #B84E2F)",
            cursor: "pointer"
          }}
          title={t("switch_role")}
        >
          {t("switch_role") || "Switch"}
        </button>
      </div>
    </header>
  );
};

export default Header;

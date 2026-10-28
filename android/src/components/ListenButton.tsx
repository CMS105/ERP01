import React from "react";
import { Volume2, VolumeX } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

interface ListenButtonProps {
  text: string;
}

export const ListenButton: React.FC<ListenButtonProps> = ({ text }) => {
  const { speak, isSpeaking, t } = useLanguage();

  return (
    <button
      type="button"
      className={`listen-button ${isSpeaking ? "playing" : ""}`}
      onClick={(e) => {
        e.stopPropagation();
        speak(text);
      }}
      aria-label={t("listen")}
      title={t("listen")}
    >
      {isSpeaking ? <VolumeX size={13} /> : <Volume2 size={13} />}
      <span>{t("listen")}</span>
    </button>
  );
};

export default ListenButton;

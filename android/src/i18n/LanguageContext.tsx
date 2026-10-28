import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import stringsData from "./strings.json";

type Language = "en" | "kn";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, defaultText?: string) => string;
  speak: (text: string) => void;
  isSpeaking: boolean;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    return (localStorage.getItem("lpg_language") as Language) || "en";
  });
  const [isSpeaking, setIsSpeaking] = useState(false);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("lpg_language", lang);
    if (lang === "kn") {
      document.documentElement.classList.add("kn");
    } else {
      document.documentElement.classList.remove("kn");
    }
  };

  useEffect(() => {
    if (language === "kn") {
      document.documentElement.classList.add("kn");
    } else {
      document.documentElement.classList.remove("kn");
    }
  }, [language]);

  const t = (key: string, defaultText?: string): string => {
    const langStrings = (stringsData as Record<string, Record<string, string>>)[language];
    if (langStrings && langStrings[key]) {
      return langStrings[key];
    }
    const enStrings = (stringsData as Record<string, Record<string, string>>)["en"];
    if (enStrings && enStrings[key]) {
      return enStrings[key];
    }
    return defaultText || key;
  };

  const speak = (text: string) => {
    if (!("speechSynthesis" in window)) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === "kn" ? "kn-IN" : "en-IN";
    utterance.rate = 0.9;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, speak, isSpeaking }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};

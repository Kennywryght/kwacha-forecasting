import React, { createContext, useContext, useState } from "react";

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState("en");

  const t = {
    en: {
      dashboard: "Dashboard",
      history: "History",
      models: "Models",
      home: "Home",
      about: "About",
    },
    ny: {
      dashboard: "Dashibodi",
      history: "Mbiri",
      models: "Ma Model",
      home: "Kunyumba",
      about: "Za ife",
    },
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t: t[lang] }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
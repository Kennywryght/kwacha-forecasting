import React, { createContext, useContext, useState } from 'react';

const LanguageContext = createContext();

const translations = {
  en: {
    // Navbar
    home: "Home",
    dashboard: "Dashboard",
    history: "History",
    about: "About",
    admin: "Admin Dashboard",
    
    // Dashboard
    kwachaCast: "KwachaCast",
    exchangeRateForecasts: "Exchange rate forecasts for the Malawi Kwacha",
    export: "Export",
    refresh: "Refresh",
    refreshForecasts: "Refresh forecasts",
    generating: "Generating...",
    currentRate: "Current rate",
    nextDay: "Next day",
    sevenDays: "7 days",
    thirtyDays: "30 days",
    forecastOutlook: "Forecast outlook",
    projectedMovement: "Projected Kwacha movement across timeframes.",
    daysAhead: "Days ahead",
    whatYouShouldDo: "What you should do",
    guidanceBased: "Guidance based on forecast at MWK",
    today: "Today",
    thisWeek: "This week",
    thisMonth: "This month",
    stable: "Stable",
    weakening: "Weakening",
    strengthening: "Strengthening",
    noActionNeeded: "No action needed — rate is holding steady.",
    continueRegular: "Continue with your regular transactions.",
    kwachaMayLose: "Kwacha may lose ~{pct}% of value.",
    kwachaMayGain: "Kwacha may gain ~{pct}% against USD.",
    buySooner: "If you need USD for imports, school fees, or travel, buy sooner rather than later.",
    convertNow: "If you hold USD, convert to Kwacha now. Importers can wait for better rates.",
    expected: "Expected",
    
    // Who This Affects
    howThisAffects: "How this affects you",
    groceries: "Buying groceries & goods",
    students: "Students & parents",
    business: "Business owners",
    remittances: "Receiving money from abroad",
    
    // Trust & Stats
    accuracyTransparency: "Accuracy & transparency",
    ourForecasts: "Our forecasts (dotted) vs actual rates.",
    historicalRates: "Historical rates for the last 30 days.",
    actualRate: "Actual rate",
    ourForecast: "Our forecast",
    rateStatistics: "Rate statistics",
    modelAccuracy: "Model accuracy",
    historicalTrends: "Historical trends",
    
    // Key Insight
    kwachaExpected: "The Kwacha is expected to remain stable at ~MWK {rate} this week.",
    kwachaMove: "The Kwacha is expected to move by {pct}% over the next 7 days ({direction}).",
    modelErrorRate: "Our models have a {error}% error rate based on {points} historical comparisons.",
    
    // FAQ
    quickAnswers: "Quick answers",
    howOften: "How often are forecasts updated?",
    howOftenAnswer: "Forecasts are generated daily. Click \"Refresh\" to get the latest predictions.",
    whatStrengthening: "What does \"Strengthening\" mean?",
    whatStrengtheningAnswer: "It means the Kwacha is gaining value. You need fewer Kwacha to buy 1 USD.",
    howAccurate: "How accurate are these forecasts?",
    howAccurateAnswer: "Our models achieve 0.30% MAPE — predictions are typically within 5 MWK of the actual rate.",
    whereData: "Where does the data come from?",
    whereDataAnswer: "Exchange rates from the Reserve Bank of Malawi and live currency APIs. Updated daily.",
    
    // General
    disclaimer: "Forecasts are for informational purposes. Exchange rates are influenced by central bank policy, import demand, and global conditions. Past accuracy does not guarantee future results.",
    noForecasts: "No forecasts yet",
    clickGenerate: "Click below to generate today's exchange rate forecasts.",
    generateForecasts: "Generate forecasts",
    forecastsUpdated: "Forecasts updated!",
    failedBackend: "Failed. Backend may be waking up — try again.",
    lastUpdated: "Last updated",
    never: "Never",
    liveExchangeRate: "Live exchange rate",
  },
  
  ny: {
    // Navbar
    home: "Kunyumba",
    dashboard: "Dashibodi",
    history: "Mbiri",
    about: "Za Ife",
    admin: "Admin Dashboard",
    
    // Dashboard
    kwachaCast: "KwachaCast",
    exchangeRateForecasts: "Zolosera za mtengo wa Kwacha ya Malawi",
    export: "Tumiza",
    refresh: "Yambitsaninso",
    refreshForecasts: "Yambitsaninso zolosera",
    generating: "Tikupanga...",
    currentRate: "Mtengo wapano",
    nextDay: "Mawa",
    sevenDays: "Masiku 7",
    thirtyDays: "Masiku 30",
    forecastOutlook: "Zolosera zamtsogolo",
    projectedMovement: "Kuyenda kwa Kwacha mtsogolo.",
    daysAhead: "Masiku akutsogolo",
    whatYouShouldDo: "Zoyenera kuchita",
    guidanceBased: "Ulangizi potengera zolosera pa MWK",
    today: "Lero",
    thisWeek: "Mlungu uno",
    thisMonth: "Mwezi uno",
    stable: "Yokhazikika",
    weakening: "Kuchepa mphamvu",
    strengthening: "Kukula mphamvu",
    noActionNeeded: "Palibe choyenera kuchita — mtengo ukukhazikika.",
    continueRegular: "Pitilizani ndi zochita zanu zamasiku onse.",
    kwachaMayLose: "Kwacha ikhoza kutaya pafupifupi {pct}% ya mtengo wake.",
    kwachaMayGain: "Kwacha ikhoza kukula pafupifupi {pct}% motsutsana ndi USD.",
    buySooner: "Ngati mukufuna USD, gulani msanga musanakwere.",
    convertNow: "Ngati muli ndi USD, sinthani kukhala Kwacha tsopano.",
    expected: "Kuyembekezera",
    
    // Who This Affects
    howThisAffects: "Momwe izi zimakhudzira inu",
    groceries: "Kugula zakudya & katundu",
    students: "Ophunzira & makolo",
    business: "Amalonda",
    remittances: "Kulandira ndalama kuchokera kunja",
    
    // Trust & Stats
    accuracyTransparency: "Kulondola & kuwonekera",
    ourForecasts: "Zolosera zathu (mizere) vs mitengo yeniyeni.",
    historicalRates: "Mitengo yamasiku 30 apitawa.",
    actualRate: "Mtengo weniweni",
    ourForecast: "Zolosera zathu",
    rateStatistics: "Ziwerengero za mtengo",
    modelAccuracy: "Kulondola kwa model",
    historicalTrends: "Zochitika zakale",
    
    // Key Insight
    kwachaExpected: "Kwacha ikuyembekezeka kukhazikika pa ~MWK {rate} mlungu uno.",
    kwachaMove: "Kwacha ikuyembekezeka kusuntha ndi {pct}% m'masiku 7 ({direction}).",
    modelErrorRate: "Ma model athu ali ndi zolakwa za {error}% potengera {points} zofanizira zakale.",
    
    // FAQ
    quickAnswers: "Mayankho achidule",
    howOften: "Zolosera zimasinthidwa kangati?",
    howOftenAnswer: "Zolosera zimapangidwa tsiku ndi tsiku. Dinani \"Yambitsaninso\" kuti mupeze zaposachedwa.",
    whatStrengthening: "\"Kukula mphamvu\" kumatanthauza chiyani?",
    whatStrengtheningAnswer: "Kumatanthauza kuti Kwacha ikukula mtengo. Mukufuna Kwacha zochepa kugula 1 USD.",
    howAccurate: "Zolosera izi ndi zolondola bwanji?",
    howAccurateAnswer: "Ma model athu amakwaniritsa 0.30% MAPE — zolosera zimakhala mkati mwa 5 MWK ya mtengo weniweni.",
    whereData: "Deta imachokera kuti?",
    whereDataAnswer: "Mitengo yosinthanitsa kuchokera ku Reserve Bank of Malawi ndi ma API amoyo. Zimasinthidwa tsiku ndi tsiku.",
    
    // General
    disclaimer: "Zolosera ndi zongodziwitsa. Mitengo yosinthanitsa imakhudzidwa ndi mfundo za banki yayikulu, kufunikira kwa katundu, ndi zochitika zapadziko lonse.",
    noForecasts: "Palibe zolosera",
    clickGenerate: "Dinani pansipa kuti mupange zolosera za lero.",
    generateForecasts: "Pangani zolosera",
    forecastsUpdated: "Zolosera zasinthidwa!",
    failedBackend: "Zalephera. Backend ikhoza kukhala ikudzuka — yesaninso.",
    lastUpdated: "Kusinthidwa komaliza",
    never: "Sizinachitikepo",
    liveExchangeRate: "Mtengo wamoyo",
  }
};

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState('en');
  
  const t = (key, params = {}) => {
    let text = translations[lang]?.[key] || translations.en[key] || key;
    // Replace parameters like {pct}, {rate}, etc.
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(`{${k}}`, v);
    });
    return text;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
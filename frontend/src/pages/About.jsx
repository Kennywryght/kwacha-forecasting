import React from "react";
import { useLanguage } from "../context/LanguageContext";
import {
  AlertCircle,
  BookOpen,
  Code,
  BarChart3,
  TrendingUp,
} from "lucide-react";

export default function About() {
  const { lang } = useLanguage();

  const t = (en, ny) => (lang === "ny" ? ny : en);

  return (
    <div className="max-w-5xl mx-auto px-6 py-12 space-y-12 text-white">
      {/* Hero */}
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">
          {t("About MWK Forecast", "Za Kwacha Forecast")}
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-lg">
          {t(
            "A data science project forecasting Malawi Kwacha exchange rates using advanced statistical modeling.",
            "Pulojekiti ya data science yolosa mtengo wa Kwacha ya Malawi pogwiritsa ntchito masamu apamwamba."
          )}
        </p>
      </div>

      {/* Mission */}
      <div className="bg-blue-900/20 border-l-4 border-blue-500 rounded-xl p-6">
        <h2 className="text-2xl font-bold text-blue-300 mb-3">
          {t("Our Mission", "Cholinga Chathu")}
        </h2>
        <p className="text-blue-200/80 leading-relaxed">
          {t(
            "To provide accessible, accurate, and transparent exchange rate forecasts that empower businesses and individuals.",
            "Kupereka zolosera zolondola komanso zomveka za mtengo wa ndalama kuti zithandize mabizinesi ndi anthu wamba."
          )}
        </p>
      </div>

      {/* Methodology */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Code className="w-8 h-8 text-blue-400" />
          <h2 className="text-2xl font-bold">
            {t("Methodology", "Njira Zathu")}
          </h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="font-semibold text-lg mb-2">
              {t("Statistical Approach", "Njira za Masamu")}
            </h3>
            <ul className="space-y-2 text-slate-300">
              <li>
                <strong>ARIMA:</strong>{" "}
                {t(
                  "Univariate model capturing temporal patterns.",
                  "Model wamtundu umodzi wozindikira machitidwe anthawi."
                )}
              </li>
              <li>
                <strong>ARIMAX:</strong>{" "}
                {t(
                  "Extends ARIMA with economic drivers (15% more accurate).",
                  "Amaphatikiza zinthu za chuma (15% olondola kwambiri)."
                )}
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-lg mb-2">
              {t("Data Sources", "Magwero a Data")}
            </h3>
            <ul className="list-disc ml-5 text-slate-300 space-y-1">
              <li>{t("Exchange Rates: Investing.com", "Mitengo: Investing.com")}</li>
              <li>{t("Inflation: IMF IFS", "Kukwera kwa mitengo: IMF")}</li>
              <li>{t("Foreign Reserves: RBM", "Ndalama Zakunja: RBM")}</li>
              <li>{t("Money Supply: RBM", "Kuchuluka kwa ndalama: RBM")}</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Validation & Performance */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 className="w-8 h-8 text-purple-400" />
          <h2 className="text-2xl font-bold">
            {t("Validation & Performance", "Kutsimikiza ndi Kuyenda")}
          </h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-4">
          <div>
            <h3 className="font-semibold text-lg">
              {t("Evaluation Metrics", "Miyeso ya Kuyesa")}
            </h3>
            <p className="text-slate-300">
              {t(
                "RMSE, MAE, MAPE, 95% confidence intervals.",
                "RMSE, MAE, MAPE, magawo a 95%."
              )}
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-lg">
              {t("Statistical Testing", "Kuyesa kwa Masamu")}
            </h3>
            <ul className="list-disc ml-5 text-slate-300 space-y-1">
              <li>{t("Diebold-Mariano test (p < 0.001)", "Mayeso a Diebold-Mariano")}</li>
              <li>{t("Rolling window validation", "Kutsimikiza kwa mawindo osintha")}</li>
              <li>{t("94.2% actuals within 95% CI", "94.2% zolondola mkati mwa 95%")}</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <AlertCircle className="w-8 h-8 text-amber-400" />
          <h2 className="text-2xl font-bold">
            {t("Important Disclaimers", "Chenjezo Lofunika")}
          </h2>
        </div>
        <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-6 space-y-3 text-amber-100/90">
          <p className="font-semibold">
            {t("For informational purposes only.", "Zongofuna kudziwitsa basi.")}
          </p>
          <ul className="list-disc ml-5 space-y-2 text-sm">
            <li>{t("Not financial advice.", "Osati uphungu wa ndalama.")}</li>
            <li>{t("No guarantee of accuracy.", "Palibe chitsimikizo cha kulondola.")}</li>
            <li>{t("Use at your own risk.", "Zitani pa ngozi yanu.")}</li>
          </ul>
        </div>
      </section>

      {/* API Documentation */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Code className="w-8 h-8 text-green-400" />
          <h2 className="text-2xl font-bold">
            {t("API Documentation", "Malangizo a API")}
          </h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-4">
          <p className="text-slate-300">
            {t(
              "REST API endpoints for programmatic access.",
              "Ma endpoint a REST API oti mufikire mopanda munthu."
            )}
          </p>
          <div className="bg-slate-950 text-slate-300 rounded p-4 font-mono text-sm space-y-3">
            <div>
              <span className="text-green-400">GET /api/v1/rates/latest</span>
              <p className="text-slate-500">Returns current rate and 7-day forecast</p>
            </div>
            <div>
              <span className="text-green-400">GET /api/v1/forecasts/all</span>
              <p className="text-slate-500">All model forecasts</p>
            </div>
            <div>
              <span className="text-green-400">POST /api/v1/forecasts/generate</span>
              <p className="text-slate-500">Trigger new forecast generation</p>
            </div>
          </div>
          <div>
            <h3 className="font-semibold text-lg mb-2">
              {t("Response Format", "Mawonekedwe a Yankho")}
            </h3>
            <pre className="bg-slate-950 p-4 rounded text-sm text-slate-300 overflow-x-auto">
{`{
  "success": true,
  "data": { ... },
  "timestamp": "2025-05-11T14:30:00Z",
  "notes": "Forecasts for informational purposes only"
}`}
            </pre>
          </div>
        </div>
      </section>

      {/* Project Information */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-8 h-8 text-slate-300" />
          <h2 className="text-2xl font-bold">
            {t("Project Information", "Zambiri za Pulojekiti")}
          </h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-semibold">
                {t("Researcher", "Wofufuza")}
              </h4>
              <p className="text-slate-300">Kennedy Banda (BSDS0221)</p>
              <p className="text-slate-400 text-sm">
                {t("Data Science, MZUZU University", "Data Science, Mzuzu University")}
              </p>
            </div>
            <div>
              <h4 className="font-semibold">
                {t("Supervisor", "Woyang'anira")}
              </h4>
              <p className="text-slate-300">Dr. Ruben Moyo</p>
              <p className="text-slate-400 text-sm">{t("Faculty of ICT", "Faculty ya ICT")}</p>
            </div>
            <div>
              <h4 className="font-semibold">
                {t("Project Type", "Mtundu wa Pulojekiti")}
              </h4>
              <p className="text-slate-300">{t("Research Proposal", "Research Proposal")}</p>
              <p className="text-slate-400 text-sm">{t("Data Science Capstone", "Data Science Capstone")}</p>
            </div>
            <div>
              <h4 className="font-semibold">
                {t("Technologies", "Matekinoloje")}
              </h4>
              <p className="text-slate-300">Python, React, FastAPI, PostgreSQL</p>
              <p className="text-slate-400 text-sm">ARIMA, ARIMAX, Statsmodels</p>
            </div>
          </div>
          <div>
            <h4 className="font-semibold mb-2">
              {t("Key Deliverables", "Zotsatira Zazikulu")}
            </h4>
            <ul className="list-disc ml-5 text-slate-300 space-y-1">
              <li>{t("Production-ready forecasting models", "Ma model okonzeka kugwira ntchito")}</li>
              <li>{t("Interactive web dashboard", "Dashibodi yapaintaneti")}</li>
              <li>{t("Automated daily data pipeline", "Njira yodzithandiza ya data ya tsiku ndi tsiku")}</li>
              <li>{t("REST API", "REST API")}</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <div className="bg-gradient-to-r from-blue-900/30 to-slate-800 border border-blue-500/30 rounded-xl p-8 text-center">
        <h3 className="text-2xl font-bold mb-3">
          {t("Questions or Feedback?", "Mafunso kapena Ndemanga?")}
        </h3>
        <p className="text-slate-400 mb-6 max-w-2xl mx-auto">
          {t(
            "We welcome suggestions for improvement.",
            "Tikulandira malingaliro opititsa patsogolo."
          )}
        </p>
        <div className="space-y-2 text-slate-300">
          <p>Email: <a href="mailto:kbanda@mzuzuuni.mw" className="text-blue-400 hover:underline">kbanda@mzuzuuni.mw</a></p>
          <p>Supervisor: <a href="mailto:rmoyo@mzuzuuni.mw" className="text-blue-400 hover:underline">rmoyo@mzuzuuni.mw</a></p>
        </div>
      </div>
    </div>
  );
}
import re

with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix KPI values
content = content.replace(
    'const sevenDayVal = forecast7d?.predicted_rate?.toFixed(2) ?? null;',
    'const sevenDayVal = forecast7d?.predicted_rate?.toFixed(2) ?? forecast7d?.forecasts?.[6]?.predicted_rate?.toFixed(2) ?? null;'
)
content = content.replace(
    'const thirtyDayVal = forecast30d?.predicted_rate?.toFixed(2) ?? null;',
    'const thirtyDayVal = forecast30d?.predicted_rate?.toFixed(2) ?? forecast30d?.forecasts?.[29]?.predicted_rate?.toFixed(2) ?? null;'
)
content = content.replace(
    'const sevenDayChange = forecast7d ? getChange(forecast7d.predicted_rate) : null;',
    'const sevenDayChange = forecast7d ? getChange(forecast7d.predicted_rate || forecast7d?.forecasts?.[6]?.predicted_rate) : null;'
)
content = content.replace(
    'const thirtyDayChange = forecast30d ? getChange(forecast30d.predicted_rate) : null;',
    'const thirtyDayChange = forecast30d ? getChange(forecast30d.predicted_rate || forecast30d?.forecasts?.[29]?.predicted_rate) : null;'
)

# Fix ForecastOutlook deduplication
old_outlook = '''function ForecastOutlook({ forecast1d, forecast7d, forecast30d }) {
  const allData = [];
  if (forecast1d?.predicted_rate) allData.push({ day: 1, value: Number(forecast1d.predicted_rate?.toFixed(2)), horizon: "Next day", date: fmtDate(forecast1d.target_date) });
  if (forecast7d?.forecasts) forecast7d.forecasts.forEach((v, i) => allData.push({ day: i + 1, value: Number(v?.predicted_rate?.toFixed(2)), horizon: "7 days", date: fmtDate(v?.target_date) }));
  if (forecast30d?.forecasts) forecast30d.forecasts.forEach((v, i) => allData.push({ day: i + 1, value: Number(v?.predicted_rate?.toFixed(2)), horizon: "30 days", date: fmtDate(v?.target_date) }));
  if (!allData.length) return null;'''

new_outlook = '''function ForecastOutlook({ forecast1d, forecast7d, forecast30d }) {
  const allData = [];
  const seenDates = new Set();
  
  if (forecast1d?.predicted_rate && forecast1d?.target_date) {
    const d = forecast1d.target_date;
    if (!seenDates.has(d)) { seenDates.add(d); allData.push({ day: 1, value: Number(forecast1d.predicted_rate?.toFixed(2)), horizon: "Next day", date: fmtDate(d) }); }
  }
  
  if (forecast7d?.forecasts) {
    forecast7d.forecasts.forEach((v, i) => {
      const d = v?.target_date;
      if (d && !seenDates.has(d)) { seenDates.add(d); allData.push({ day: i + 1, value: Number(v?.predicted_rate?.toFixed(2)), horizon: "7 days", date: fmtDate(d) }); }
    });
  }
  
  if (forecast30d?.forecasts) {
    forecast30d.forecasts.forEach((v, i) => {
      const d = v?.target_date;
      if (d && !seenDates.has(d)) { seenDates.add(d); allData.push({ day: i + 1, value: Number(v?.predicted_rate?.toFixed(2)), horizon: "30 days", date: fmtDate(d) }); }
    });
  }
  
  if (!allData.length) return null;'''

content = content.replace(old_outlook, new_outlook)

with open('frontend/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed successfully')

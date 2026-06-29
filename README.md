# 🇲🇼 KwachaCast — MWK/USD Exchange Rate Forecasting

[![Deploy](https://img.shields.io/badge/Deploy-Automated-blue)](https://github.com/Kennywryght/kwacha-forecasting/actions)
[![API](https://img.shields.io/badge/API-Live-green)](https://kwachacast-api.onrender.com/docs)
[![Dashboard](https://img.shields.io/badge/Dashboard-Live-brightgreen)](https://kwachacast.vercel.app)

An AI-powered forecasting system for the Malawi Kwacha exchange rate, achieving **0.30% MAPE** (average error of ~5 MWK). Built as a Data Science capstone project at Mzuzu University.

**Live Dashboard:** [kwachacast.vercel.app](https://kwachacast.vercel.app)  
**API Documentation:** [kwachacast-api.onrender.com/docs](https://kwachacast-api.onrender.com/docs)

---

## 📊 Project Overview

KwachaCast helps businesses and individuals in Malawi make informed financial decisions by providing daily MWK/USD exchange rate forecasts with confidence intervals. The system analyzes 13+ years of historical data using an ensemble of 5 forecasting models.

### Key Features

- 🔮 **Multi-horizon forecasts**: 1-day, 7-day, and 30-day predictions
- 📈 **Confidence intervals**: 95% prediction intervals on all forecasts
- 🤖 **Ensemble of 5 models**: ARIMA, ARIMAX, Prophet, XGBoost, LightGBM
- 📊 **Interactive dashboard**: Real-time charts with actionable insights
- 📱 **PWA support**: Install on mobile devices, works offline
- 🔄 **Daily updates**: Fresh forecasts every business day
- 📤 **Data export**: Download forecasts as CSV/JSON

---

## 🎯 Model Performance

Evaluated on a 15% held-out test set (time-based split, no data leakage):

| Metric | Value | Description |
|--------|-------|-------------|
| **MAPE** | **0.30%** | Mean Absolute Percentage Error |
| **RMSE** | **4.88 MWK** | Root Mean Square Error |
| **R²** | **0.991** | Coefficient of Determination |
| **Directional Accuracy** | **78%** | Correct up/down predictions |

*At the current rate of ~1,735 MWK/USD, a 0.30% MAPE means predictions are typically within 5 MWK of the actual rate.*

---

## 🏗️ System Architecture


---

## 🔬 How It Works

### Data Pipeline
1. **Data Collection**: Historical MWK/USD rates (2013–present) from the Reserve Bank of Malawi, supplemented with live currency APIs
2. **Feature Engineering**: 42 features created including lag values, rolling statistics, momentum indicators, cyclical temporal encodings, and macroeconomic differentials
3. **Train/Test Split**: 85% training (2013–2024), 15% testing (2024–2026) — time-based to prevent data leakage

### Models
| Model | Type | Description |
|-------|------|-------------|
| ARIMA | Statistical | Baseline with auto-order selection via AIC |
| ARIMAX | Statistical | ARIMA enhanced with exogenous economic indicators |
| Prophet | Decomposition | Facebook Prophet with changepoint detection |
| XGBoost | Gradient Boosting | Best individual performer |
| LightGBM | Gradient Boosting | Leaf-wise growth for efficiency |
| Ensemble | Weighted Average | Combines all models by RMSE performance |

### Evaluation Metrics
- **MAPE (Mean Absolute Percentage Error)**: Primary metric — intuitive percentage error
- **RMSE (Root Mean Square Error)**: Penalizes large errors heavily
- **R² (Coefficient of Determination)**: Variance explained by the model
- **Directional Accuracy**: Correct prediction of up/down movement

---

## 📁 Project Structure
kwacha-forecasting/
│
├── backend/
│ ├── api/routes/ # FastAPI endpoints (forecasts, rates, models)
│ ├── core/ # Configuration & logging
│ ├── db/ # Database models, CRUD operations
│ ├── ml/
│ │ ├── artifacts/ # Trained model files (.pkl, .joblib)
│ │ ├── models/ # ARIMA, ARIMAX, Prophet, Ensemble
│ │ ├── pipeline/ # Feature engineering, data pipeline
│ │ └── utils/ # Metrics, training utilities
│ ├── main.py # FastAPI application entry point
│ └── requirements.txt # Python dependencies
│
├── frontend/
│ └── src/
│ ├── components/ # Reusable UI components
│ ├── pages/ # Dashboard, History, About, Admin
│ ├── hooks/ # Custom React hooks
│ ├── utils/ # API client, helpers
│ └── context/ # App state management
│
├── data/
│ ├── raw/ # Original CSV data
│ └── processed/ # Cleaned & engineered data
│
├── docs/ # Documentation
├── tests/ # Test suite
├── scripts/ # Automation scripts
├── .github/workflows/ # CI/CD pipeline
└── README.md # This file


---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **SQLite** (development) or **PostgreSQL** (production)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/Kennywryght/kwacha-forecasting.git
cd kwacha-forecasting

# Set up Python environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize database and train models
python seed_db.py
python train_models.py

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

The API will be available at http://localhost:8000
API documentation at http://localhost:8000/docs

Frontend Setup
# In a new terminal
cd frontend
npm install
npm run dev

The dashboard will be available at http://localhost:5173

Environment Variables
Create a .env file in the backend/ directory: DATABASE_URL=sqlite:///./kwachacast.db

Create a .env file in the frontend/ directory:VITE_API_URL=http://localhost:8000/api/v1

 Documentation
Methodology — Detailed explanation of the forecasting approach

API Reference — Complete API endpoint documentation

Model Card — Model details, performance, and limitations

User Guide — How to use the application

Running Tests
cd backend
pytest tests/ -v

Deployment
The project is deployed using:

Backend: Render — automatic deployment from GitHub

Frontend: Vercel — automatic deployment on push to main

CI/CD: GitHub Actions — automated build and deploy pipeline

Limitations & Disclaimer
1.Forecasts are informational only — not financial advice

2. Accuracy depends on Malawi's managed exchange rate policy — structural changes (devaluations) may temporarily reduce accuracy

3. Exogenous variable forecasts assume current conditions persist — inflation and interest rates are held constant for future predictions

4. Past accuracy does not guarantee future performance

5. Not suitable for intraday trading — designed for daily horizon

 

👤 Author
Kennedy Banda
Data Science Capstone Project
Department of Information and Communication Technology
Mzuzu University, 2026

Supervisor: Dr. Ruben Moyo

📄 License
This project is created for academic purposes as a Data Science capstone project at Mzuzu University.

🙏 Acknowledgments
Reserve Bank of Malawi for exchange rate data

Open Exchange Rates API for live rate data

Statsmodels, Scikit-learn, XGBoost, LightGBM, and Prophet libraries

Render and Vercel for hosting


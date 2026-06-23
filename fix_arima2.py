with open('backend/ml/models/arima_model.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix ARIMA predict
old_pred = 'predicted = forecast.predicted_mean.values'
new_pred = '''predicted_raw = forecast.predicted_mean
    if hasattr(predicted_raw, 'values'):
        predicted = predicted_raw.values
    elif hasattr(predicted_raw, 'tolist'):
        predicted = predicted_raw.tolist()
    else:
        predicted = list(predicted_raw)'''

content = content.replace(old_pred, new_pred)

# Fix confidence intervals
old_conf = '''if isinstance(conf_int, pd.DataFrame):
                lower = conf_int.iloc[:, 0].values
                upper = conf_int.iloc[:, 1].values
            else:
                lower = conf_int[:, 0]
                upper = conf_int[:, 1]'''

new_conf = '''if isinstance(conf_int, pd.DataFrame):
                lower = conf_int.iloc[:, 0].tolist()
                upper = conf_int.iloc[:, 1].tolist()
            else:
                lower = conf_int[:, 0].tolist() if hasattr(conf_int[:, 0], 'tolist') else list(conf_int[:, 0])
                upper = conf_int[:, 1].tolist() if hasattr(conf_int[:, 1], 'tolist') else list(conf_int[:, 1])'''

content = content.replace(old_conf, new_conf)

with open('backend/ml/models/arima_model.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('ARIMA model fixed')

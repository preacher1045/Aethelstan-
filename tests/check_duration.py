import json

data = json.load(open('data/processed/2023_test_features.json'))
print(f'Windows: {len(data)}')
print(f'First window: {data[0]["window_start"]}')
print(f'Last window: {data[-1]["window_end"]}')
duration = (data[-1]['window_end'] - data[0]['window_start']) / 60
print(f'Total duration: {duration:.1f} minutes')
print(f'\nCurrent window size: 60 seconds')
print(f'To get more training data, reduce to 10-30 seconds')
print(f'With 10s windows: ~{int(duration * 6)} windows')
print(f'With 30s windows: ~{int(duration * 2)} windows')

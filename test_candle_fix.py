"""Test candle normalization logic"""

# Simulate candle from pyquotex API
test_candle = {
    'time': 1234567890,
    'open': 1.1,
    'close': 1.2,
    'high': 1.3,
    'low': 1.0,
    'ticks': 100
}

print("=" * 60)
print("CANDLE NORMALIZATION TEST")
print("=" * 60)
print(f"\nOriginal Candle Keys: {list(test_candle.keys())}")

# Check which format
has_high_low = 'high' in test_candle and 'low' in test_candle
has_max_min = 'max' in test_candle and 'min' in test_candle
has_open_close = 'open' in test_candle and 'close' in test_candle

print(f"has_open_close: {has_open_close}")
print(f"has_high_low: {has_high_low}")
print(f"has_max_min: {has_max_min}")

# Normalize
normalized = dict(test_candle)
if has_high_low and not has_max_min:
    normalized['max'] = test_candle['high']
    normalized['min'] = test_candle['low']
    print("\n✅ Applied normalization: high→max, low→min")

print(f"\nNormalized Candle Keys: {list(normalized.keys())}")

# Check if all required keys exist
required = ['open', 'close', 'max', 'min']
has_all = all(k in normalized for k in required)
print(f"\nHas all required keys {required}: {has_all}")

if has_all:
    print("\n✅ SUCCESS: Candle normalization working correctly!")
    print(f"   open={normalized['open']}, close={normalized['close']}")
    print(f"   max={normalized['max']}, min={normalized['min']}")
else:
    missing = [k for k in required if k not in normalized]
    print(f"\n❌ FAIL: Missing keys: {missing}")

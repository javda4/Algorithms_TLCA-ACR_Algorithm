# TLCA-ACR: Time-Location-Context-Aware Adaptive Cache Replacement

**Author:** Joshua Van Doren  
 

---

## 📘 Overview

**TLCA-ACR (Time-Location-Context-Aware Adaptive Cache Replacement)** is an intelligent, real-time caching algorithm that uses multi-dimensional signals—**frequency**, **recency**, **time**, **location**, and **contextual heuristics**—to make proactive cache replacement decisions. It outperforms traditional policies like LRU/LFU in time-sensitive, location-aware, or context-dependent environments such as **mobile apps**, **edge computing**, or **IoT systems**.

---

## 🔍 Motivation

Conventional cache algorithms like **LRU** (Least Recently Used) and **LFU** (Least Frequently Used) only consider basic patterns such as access recency or frequency. However, in real-world environments:

- **Time of day** affects user behavior (e.g., peak vs. off-peak usage)
- **User location** can change data priority (e.g., GPS-based apps)
- **Device context** (e.g., gaming mode, low battery) can influence cache value

These signals are ignored by standard algorithms. TLCA-ACR incorporates them into its scoring to make **more informed** and **application-aware** caching decisions.

---

## 📐 Scoring Formula


```Score(T) = α⋅freq + β⋅(1/recency) + γ⋅context_value + δ⋅time_weight(t) + ϵ⋅location_weight(x, y)```


Where:
- `freq`: Access frequency
- `recency`: Time since last access
- `context_value`: Heuristic signal (e.g., device mode, user behavior)
- `time_weight(t)`: Time-of-day importance
- `location_weight(x, y)`: Spatial importance
- `α-ϵ`: Tunable weights per application

---

## 🚀 Features

- ✅ Adaptive scoring based on frequency, recency, time, location, and custom context
- ✅ Pluggable scoring functions for time and location weighting
- ✅ Tie-breaker eviction logic for fairness in scoring collisions
- ✅ Real-time simulation support with runtime and memory measurement
- ✅ Well-commented and extensible Python implementation

---

## 🛠️ How It Works

- Call `put(key, value, t, loc)` to add or update cache entries.
- Call `get(key, t, loc)` to retrieve a value and update access metadata.
- Custom `context_fn`, `time_fn`, and `loc_fn` can be passed to shape behavior.

```python
cache.set_context_functions(
    context_fn=lambda: 1.0,
    time_fn=lambda t: 2.0 if 8 <= t <= 10 else 0.5,
    loc_fn=lambda x, y: 2.0 if (x, y) == (37.77, -122.42) else 0.5
)
cache.put("A", "Apple", t=9, loc=(37.77, -122.42))
value = cache.get("A", t=9, loc=(37.77, -122.42))
```

## ▶️ How to Run

- Python 3.6+
- No external libraries needed

```
python tlca_acr_cache.py
```

## Future modifications
- cli usability
- access to dataset implementation
- Faster implementation of extensive amounts of context functions



# Joshua Van Doren
# Red ID: 825113101

import time
import tracemalloc  # For tracking memory usage
from collections import defaultdict, namedtuple

# Define a structured format for cache entries (not directly used in logic, but good for clarity or expansion)
CacheEntry = namedtuple('CacheEntry', ['key', 'value', 'score'])

class TLCA_ACR_Cache:
    def __init__(self, capacity, alpha=1.0, beta=1.0, gamma=1.0, delta=1.0, epsilon=1.0):
        """
        Initialize the cache with a maximum capacity and custom weights for the scoring function.
        """
        self.capacity = capacity  # Max number of items in cache

        # Weights for scoring function
        self.alpha = alpha    # Frequency weight
        self.beta = beta      # Recency weight (recent accesses are better)
        self.gamma = gamma    # Contextual weight (external signals)
        self.delta = delta    # Time-based weight (e.g., time of day importance)
        self.epsilon = epsilon  # Location-based weight

        self.cache = {}  # Main cache storage: key -> (value, insertion_time)
        self.access_freq = defaultdict(int)  # Track how many times each key is accessed
        self.last_access = {}  # Timestamp of last access for each key

        # Default external weighting functions (can be overridden)
        self.context_fn = lambda: 1.0
        self.time_fn = lambda t: 1.0
        self.loc_fn = lambda x, y: 1.0

    def set_context_functions(self, context_fn=None, time_fn=None, loc_fn=None):
        """
        Allows users to inject custom functions for context, time, and location sensitivity.
        """
        if context_fn:
            self.context_fn = context_fn
        if time_fn:
            self.time_fn = time_fn
        if loc_fn:
            self.loc_fn = loc_fn

    def compute_score(self, key, t=None, loc=None):
        """
        Calculate the eviction score for a given cache entry.
        Higher scores mean more valuable entries.
        """
        freq = self.access_freq[key]
        recency = time.time() - self.last_access[key]  # Seconds since last access
        context_val = self.context_fn()  # External factor (e.g., system load)
        time_weight = self.time_fn(t or time.localtime().tm_hour)  # Weight based on hour of day
        loc_weight = self.loc_fn(*(loc or (0.0, 0.0)))  # Spatial relevance

        # Composite weighted score (higher is better)
        score = (self.alpha * freq +
                 self.beta * (1 / (recency + 1e-5)) +  # Prevent division by zero
                 self.gamma * context_val +
                 self.delta * time_weight +
                 self.epsilon * loc_weight)
        return score

    def get(self, key, t=None, loc=None):
        """
        Retrieve an item from the cache and update metadata (frequency, last access).
        """
        if key in self.cache:
            self.access_freq[key] += 1
            self.last_access[key] = time.time()
            return self.cache[key][0]  # Return stored value only
        return None  # Not in cache

    def put(self, key, value, t=None, loc=None):
        """
        Insert a new item into the cache. Evicts an item if over capacity.
        """
        # If key is new and cache is full, evict an entry first
        if key not in self.cache and len(self.cache) >= self.capacity:
            self.evict(t, loc)
        # Insert or update the item
        self.cache[key] = (value, time.time())
        self.access_freq[key] += 1
        self.last_access[key] = time.time()

    def evict(self, t=None, loc=None):
        """
        Evict the item with the lowest score.
        If there's a tie, evict the most recently accessed one among them.
        """
        min_score = float('inf')
        tied_keys = []

        # Determine the lowest-scoring entries
        for key in self.cache:
            score = self.compute_score(key, t, loc)
            if score < min_score:
                min_score = score
                tied_keys = [key]
            elif abs(score - min_score) < 1e-5:  # Floating point comparison tolerance
                tied_keys.append(key)

        # Resolve ties by evicting the newest (most recently accessed)
        if tied_keys:
            key_to_evict = max(tied_keys, key=lambda k: self.last_access[k])
            del self.cache[key_to_evict]
            self.access_freq.pop(key_to_evict, None)
            self.last_access.pop(key_to_evict, None)

    def current_keys(self):
        """
        Return the list of current keys in the cache (for testing/debugging).
        """
        return list(self.cache.keys())

def run_tests():
    print("\n--- TLCA-ACR Cache Test Suite ---")

    # Begin tracking memory allocations
    tracemalloc.start()
    start_time = time.perf_counter()  # Start runtime timer

    # -------------------------------
    # Test 1: Frequency + Recency Priority
    # -------------------------------
    print("\n[First Test: Frequency + Recency Priority]")
    cache = TLCA_ACR_Cache(capacity=2, alpha=2.0, beta=3.0, gamma=1.0, delta=1.0, epsilon=1.0)

    # Set custom weighting functions
    # High time weight between 8–10, and higher location score for SF coordinates
    cache.set_context_functions(
        context_fn=lambda: 1.0,
        time_fn=lambda t: 2.0 if 8 <= t <= 10 else 0.5,
        loc_fn=lambda x, y: 2.0 if (x, y) == (37.77, -122.42) else 0.5
    )

    # Insert "A" with high time and location weights
    cache.put("A", "Apple", t=9, loc=(37.77, -122.42))
    time.sleep(0.01)  # Ensure measurable time gap for recency
    # Insert "B" with lower contextual and location weights
    cache.put("B", "Banana", t=22, loc=(40.71, -74.00))

    # Access "A" twice to boost both frequency and recency
    cache.get("A", t=9, loc=(37.77, -122.42))
    time.sleep(0.01)
    cache.get("A", t=9, loc=(37.77, -122.42))

    # Insert "C", which should evict "B" (lowest score)
    cache.put("C", "Cherry", t=10, loc=(37.77, -122.42))

    # Confirm cache contains "A" and "C"
    result_keys = cache.current_keys()
    print("Expected: ['A', 'C']")
    print("Actual:  ", result_keys)
    assert "A" in result_keys
    assert "C" in result_keys
    assert "B" not in result_keys

    # -------------------------------
    # Test 2: Location/Time Context Dominates
    # Recency and frequency should have no effect
    # -------------------------------
    print("\n[Second Test: Location/Time Weight Dominance]")
    cache = TLCA_ACR_Cache(capacity=2, alpha=1.0, beta=0.0, gamma=1.0, delta=1.0, epsilon=1.0)

    # Configure cache to favor time=12 and location=(0,0)
    cache.set_context_functions(
        context_fn=lambda: 1.0,
        time_fn=lambda t: 2.0 if t == 12 else 0.1,
        loc_fn=lambda x, y: 5.0 if (x, y) == (0.0, 0.0) else 0.1
    )

    # Insert "X" with high time and location relevance
    cache.put("X", "Xray", t=12, loc=(0.0, 0.0))
    time.sleep(0.05)  # Make sure "Y" gets a different timestamp
    # Insert "Y" with weak contextual values
    cache.put("Y", "Yam", t=1, loc=(99.0, 99.0))
    time.sleep(0.05)
    # Insert "Z" with high context, should evict "Y"
    cache.put("Z", "Zebra", t=12, loc=(0.0, 0.0))

    # Confirm "X" and "Z" remain, "Y" is evicted
    result_keys = cache.current_keys()
    print("Expected: ['X', 'Z']")
    print("Actual:  ", result_keys)
    assert "X" in result_keys
    assert "Z" in result_keys
    assert "Y" not in result_keys

    # -------------------------------
    # Test 3: Tie-breaking on Score
    # Multiple entries with identical scores — evict the newest
    # -------------------------------
    print("\n[Third Test: Tie-breaking on Score]")
    cache = TLCA_ACR_Cache(capacity=2, alpha=1.0, beta=0.0, gamma=1.0, delta=1.0, epsilon=1.0)

    # Same context functions as before
    cache.set_context_functions(
        context_fn=lambda: 1.0,
        time_fn=lambda t: 2.0 if t == 12 else 0.1,
        loc_fn=lambda x, y: 5.0 if (x, y) == (0.0, 0.0) else 0.1
    )

    # Insert "X" (high score)
    cache.put("X", "Xray", t=12, loc=(0.0, 0.0))
    time.sleep(0.05)
    # Insert "Y" (low score, will get evicted later)
    cache.put("Y", "Yam", t=1, loc=(99.0, 99.0))
    time.sleep(0.05)
    # Insert "Z", should evict "Y"
    cache.put("Z", "Zebra", t=12, loc=(0.0, 0.0))
    time.sleep(0.05)
    # Insert "W", scores tie with "Z", so most recently accessed gets evicted — should keep "X" and "W"
    cache.put("W", "Wing", t=12, loc=(0.0, 0.0))

    # Validate tie-breaking logic
    result_keys = cache.current_keys()
    print("Expected: ['X', 'W']")
    print("Actual:  ", result_keys)
    assert "X" in result_keys
    assert "W" in result_keys
    assert "Y" not in result_keys
    assert "Z" not in result_keys  # Evicted due to tie-breaking

    # -------------------------------
    # Performance and Memory Profiling
    # -------------------------------
    end_time = time.perf_counter()

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\nPreliminary Runtime: {end_time - start_time:.6f} seconds")
    print(f"Current Memory Usage: {current_mem / 1024:.2f} KB")
    print(f"Peak Memory Usage: {peak_mem / 1024:.2f} KB")
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    run_tests()

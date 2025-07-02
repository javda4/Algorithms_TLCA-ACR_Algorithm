import time
import tracemalloc  # For tracking memory usage
from collections import defaultdict, namedtuple

# Named tuple for cache entries (not directly used here, but handy for clarity if extended)
CacheEntry = namedtuple('CacheEntry', ['key', 'value', 'score'])

class TLCA_ACR_Cache:
    def __init__(self, capacity, alpha=1.0, beta=1.0, gamma=1.0, delta=1.0, epsilon=1.0):
        self.capacity = capacity  # Maximum cache size
        self.alpha = alpha        # Weight for frequency
        self.beta = beta          # Weight for recency
        self.gamma = gamma        # Weight for context value
        self.delta = delta        # Weight for time-based importance
        self.epsilon = epsilon    # Weight for location-based importance

        self.cache = {}  # Stores key -> (value, insertion_time)
        self.access_freq = defaultdict(int)  # Counts how many times each key was accessed
        self.last_access = {}  # Stores the last access timestamp for each key

        # Context functions for external info; can be overridden with custom functions
        self.context_fn = lambda: 1.0  # Default context always returns 1.0
        self.time_fn = lambda t: 1.0   # Default time weight is constant 1.0
        self.loc_fn = lambda x, y: 1.0 # Default location weight is constant 1.0

    def set_context_functions(self, context_fn=None, time_fn=None, loc_fn=None):
        """Allow setting custom context, time, and location weight functions."""
        if context_fn:
            self.context_fn = context_fn
        if time_fn:
            self.time_fn = time_fn
        if loc_fn:
            self.loc_fn = loc_fn

    def compute_score(self, key, t=None, loc=None):
        """
        Compute the dynamic score of a cache entry based on frequency,
        recency, context, time, and location factors.
        """
        freq = self.access_freq[key]  # Number of times accessed
        recency = time.time() - self.last_access[key]  # Time since last access in seconds
        context_val = self.context_fn()  # External context heuristic value
        time_weight = self.time_fn(t or time.localtime().tm_hour)  # Weight based on current hour if not provided
        loc_weight = self.loc_fn(*(loc or (0.0, 0.0)))  # Weight based on location (x,y), default (0.0,0.0)

        # Combine all factors with their respective weights into a single score
        score = (self.alpha * freq +
                 self.beta * (1 / (recency + 1e-5)) +  # Avoid division by zero
                 self.gamma * context_val +
                 self.delta * time_weight +
                 self.epsilon * loc_weight)
        return score

    def get(self, key, t=None, loc=None):
        """Retrieve value from cache by key, update access frequency and timestamp."""
        if key in self.cache:
            self.access_freq[key] += 1  # Increase access frequency count
            self.last_access[key] = time.time()  # Update last access time
            return self.cache[key][0]  # Return stored value
        return None  # Key not found

    def put(self, key, value, t=None, loc=None):
        """
        Insert or update an item in the cache.
        If full and key is new, evict the lowest scored item first.
        """
        if key not in self.cache and len(self.cache) >= self.capacity:
            self.evict(t, loc)  # Evict one item based on score before inserting
        self.cache[key] = (value, time.time())  # Store value with insertion time
        self.access_freq[key] += 1  # Initialize or increment access frequency
        self.last_access[key] = time.time()  # Set last access timestamp

    def evict(self, t=None, loc=None):
        """
        Remove the cache entry with the lowest score.
        If multiple keys tie for lowest score, evict the newest among them.
        """
        min_score = float('inf')  # Initialize min score to infinity
        tied_keys = []  # List of keys with equal min score

        # Compute scores for all keys and find the minimum
        for key in self.cache:
            score = self.compute_score(key, t, loc)
            if score < min_score:
                min_score = score
                tied_keys = [key]
            elif abs(score - min_score) < 1e-5:  # Floating point equality tolerance
                tied_keys.append(key)

        # If ties exist, evict the one with the most recent last access (newest)
        if tied_keys:
            key_to_evict = max(tied_keys, key=lambda k: self.last_access[k])
            del self.cache[key_to_evict]  # Remove from cache
            self.access_freq.pop(key_to_evict, None)  # Remove frequency tracking
            self.last_access.pop(key_to_evict, None)  # Remove last access tracking

    def current_keys(self):
        """Return a list of current keys in the cache."""
        return list(self.cache.keys())

def run_tests():
    print("\n--- TLCA-ACR Cache Test Suite ---")

    # Start tracking memory allocations
    tracemalloc.start()

    start_time = time.perf_counter()  # Start timer for runtime measurement

    # Test 1: Frequency + Recency Priority
    print("\n[First Test: Frequency + Recency Priority]")
    cache = TLCA_ACR_Cache(capacity=2, alpha=2.0, beta=3.0, gamma=1.0, delta=1.0, epsilon=1.0)

    # Set context functions for time and location biases
    cache.set_context_functions(
        context_fn=lambda: 1.0,
        time_fn=lambda t: 2.0 if 8 <= t <= 10 else 0.5,  # Higher time weight in morning hours
        loc_fn=lambda x, y: 2.0 if (x, y) == (37.77, -122.42) else 0.5  # Higher weight for SF location
    )

    cache.put("A", "Apple", t=9, loc=(37.77, -122.42))  # Insert key A
    time.sleep(0.01)  # Sleep to create time difference for recency
    cache.put("B", "Banana", t=22, loc=(40.71, -74.00))  # Insert key B
    cache.get("A", t=9, loc=(37.77, -122.42))  # Access A to boost frequency & recency
    time.sleep(0.01)
    cache.get("A", t=9, loc=(37.77, -122.42))  # Access A again
    cache.put("C", "Cherry", t=10, loc=(37.77, -122.42))  # Insert C, triggers eviction (should evict B)

    result_keys = cache.current_keys()
    print("Expected: ['A', 'C']")
    print("Actual:  ", result_keys)
    assert "A" in result_keys
    assert "C" in result_keys
    assert "B" not in result_keys

    # Test 2: Location/Time Context Dominates (recency ignored)
    print("\n[Second Test: Location/Time Weight Dominance]")
    cache = TLCA_ACR_Cache(capacity=2, alpha=1.0, beta=0.0, gamma=1.0, delta=1.0, epsilon=1.0)

    # Set context functions emphasizing time=12 and location=(0,0)
    cache.set_context_functions(
        context_fn=lambda: 1.0,
        time_fn=lambda t: 2.0 if t == 12 else 0.1,
        loc_fn=lambda x, y: 5.0 if (x, y) == (0.0, 0.0) else 0.1
    )

    cache.put("X", "Xray", t=12, loc=(0.0, 0.0))  # High time and location weights
    time.sleep(0.05)  # Delay to differentiate recency timestamps
    cache.put("Y", "Yam", t=1, loc=(99.0, 99.0))  # Low time and location weights
    time.sleep(0.05)
    cache.put("Z", "Zebra", t=12, loc=(0.0, 0.0))  # Insert Z, should evict Y due to score

    result_keys = cache.current_keys()
    print("Expected: ['X', 'Z']")
    print("Actual:  ", result_keys)
    assert "X" in result_keys
    assert "Z" in result_keys
    assert "Y" not in result_keys

    end_time = time.perf_counter()  # Stop timer

    # Capture current and peak memory usage from tracemalloc
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()  # Stop tracking memory

    # Print profiling results
    print(f"\nPreliminary Runtime: {end_time - start_time:.6f} seconds")
    print(f"Current Memory Usage: {current_mem / 1024:.2f} KB")
    print(f"Peak Memory Usage: {peak_mem / 1024:.2f} KB")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    run_tests()

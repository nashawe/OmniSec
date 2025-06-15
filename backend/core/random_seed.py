# cybersec_project/backend/core/random_seed.py

import random
from typing import Optional

# --- Global Random Number Generator Instance ---
# This instance will be seeded once and then used throughout the simulation
# to ensure that sequences of random events can be reproduced if the same
# seed is used.

_simulation_rng_instance: Optional[random.Random] = None
_current_seed: Optional[int] = None

DEFAULT_SEED = 42 # A common default seed value

def initialize_rng(seed: Optional[int] = None) -> None:
    """
    Initializes or re-initializes the global random number generator (RNG)
    for the simulation with a specific seed. If no seed is provided,
    a default seed will be used.

    This should be called once at the beginning of a simulation run
    if deterministic behavior is desired.

    Args:
        seed (Optional[int], optional): The seed value for the RNG.
                                        If None, DEFAULT_SEED is used.
    """
    global _simulation_rng_instance, _current_seed
    
    if seed is None:
        effective_seed = DEFAULT_SEED
    else:
        effective_seed = seed
        
    _simulation_rng_instance = random.Random(effective_seed)
    _current_seed = effective_seed
    # print(f"Simulation RNG initialized with seed: {effective_seed}")

def get_rng() -> random.Random:
    """
    Returns the globally shared, seeded random number generator instance.
    If the RNG has not been initialized, it will be initialized with the
    DEFAULT_SEED.

    Returns:
        random.Random: The seeded RNG instance.
    """
    global _simulation_rng_instance
    if _simulation_rng_instance is None:
        initialize_rng() # Initialize with default seed if not already done
    
    # Ensure it's never None when returned, due to the check above
    return _simulation_rng_instance # type: ignore

def get_current_seed() -> Optional[int]:
    """
    Returns the seed value that the global RNG was initialized with.

    Returns:
        Optional[int]: The current seed, or None if not yet initialized
                       (though get_rng() auto-initializes).
    """
    return _current_seed

# --- Example Usage and Testing ---
if __name__ == '__main__':
    print("--- Testing Random Seed Manager ---")

    # Test 1: Initialization with default seed
    print("\nTest 1: Default Initialization")
    rng1 = get_rng() # Should initialize with DEFAULT_SEED
    print(f"Current seed: {get_current_seed()}")
    sequence1_default = [rng1.randint(0, 100) for _ in range(5)]
    print(f"Sequence 1 (default seed): {sequence1_default}")

    # Test 2: Re-initialization with a specific seed
    print("\nTest 2: Re-initialize with seed 123")
    initialize_rng(123)
    rng2 = get_rng()
    print(f"Current seed: {get_current_seed()}")
    sequence2_seed123 = [rng2.randint(0, 100) for _ in range(5)]
    print(f"Sequence 2 (seed 123): {sequence2_seed123}")

    # Test 3: Re-initialize with the same specific seed (123) should produce the same sequence
    print("\nTest 3: Re-initialize again with seed 123 (should match Sequence 2)")
    initialize_rng(123)
    rng3 = get_rng()
    print(f"Current seed: {get_current_seed()}")
    sequence3_seed123_repeat = [rng3.randint(0, 100) for _ in range(5)]
    print(f"Sequence 3 (seed 123 repeat): {sequence3_seed123_repeat}")
    assert sequence2_seed123 == sequence3_seed123_repeat, "Sequences with the same seed should match!"

    # Test 4: Initialize with default seed again (should match Sequence 1)
    print("\nTest 4: Re-initialize with default seed (should match Sequence 1)")
    initialize_rng(DEFAULT_SEED) # Explicitly use default
    # Or initialize_rng() which also uses default
    rng4 = get_rng()
    print(f"Current seed: {get_current_seed()}")
    sequence4_default_repeat = [rng4.randint(0, 100) for _ in range(5)]
    print(f"Sequence 4 (default seed repeat): {sequence4_default_repeat}")
    assert sequence1_default == sequence4_default_repeat, "Sequences with the default seed should match!"
    
    # Test 5: Accessing RNG without prior explicit initialization
    # (This scenario is covered by Test 1, as get_rng() auto-initializes)
    # To truly test this, we'd need to reset the global _simulation_rng_instance to None
    print("\nTest 5: Implicit Initialization via get_rng()")
    _simulation_rng_instance = None # Force re-initialization on next get_rng() call
    _current_seed = None
    rng5 = get_rng()
    print(f"Current seed after implicit init: {get_current_seed()}")
    sequence5_implicit_default = [rng5.randint(0, 100) for _ in range(5)]
    print(f"Sequence 5 (implicit default seed): {sequence5_implicit_default}")
    assert sequence1_default == sequence5_implicit_default, "Implicit default seed should match explicit default!"


    print("\n--- Random Seed Manager Test Complete ---")
import pytest
from app.domain.line_memory import LineMemory


def test_line_memory_store_and_lookup():
    mem = LineMemory(max_entries=3)
    user_a = "user-123"
    user_b = "user-456"
    fp1 = "sha256-abc"
    fp2 = "sha256-def"

    mem.store(user_a, fp1, "ligne corrigée A")
    assert mem.lookup(user_a, fp1) == "ligne corrigée A"

    # Isolation entre utilisateurs
    assert mem.lookup(user_b, fp1) is None

    # Deuxième entrée
    mem.store(user_a, fp2, "ligne corrigée 2")
    assert mem.lookup(user_a, fp2) == "ligne corrigée 2"


def test_line_memory_lru_eviction():
    mem = LineMemory(max_entries=2)
    user = "u1"

    mem.store(user, "fp1", "val1")
    mem.store(user, "fp2", "val2")
    mem.store(user, "fp3", "val3")  # Évince fp1

    assert mem.lookup(user, "fp1") is None
    assert mem.lookup(user, "fp2") == "val2"
    assert mem.lookup(user, "fp3") == "val3"

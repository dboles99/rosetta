from rosetta_core.hashing import sha256_text


def test_same_text_same_hash():
    assert sha256_text("abc") == sha256_text("abc")


def test_different_text_different_hash():
    assert sha256_text("abc") != sha256_text("abd")


def test_known_sha256_of_empty_string():
    assert sha256_text("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"[:64]

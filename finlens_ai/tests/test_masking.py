"""Tests for the PII masking module."""
from pipeline.masking import mask_text, restore_text


def test_mask_text_replaces_known_pii() -> None:
    text = "Mario Rossi ha depositato sul conto IT60X0542811101000000123456."
    masked, mapping = mask_text(text)

    assert "Mario Rossi" not in masked
    assert "IT60X0542811101000000123456" not in masked
    assert len(mapping) >= 2


def test_mask_text_mapping_is_invertible() -> None:
    text = "Mario Rossi, codice fiscale RSSMRA80A01H501Z."
    masked, mapping = mask_text(text)
    restored = restore_text(masked, mapping)

    assert restored == text


def test_mask_text_same_entity_gets_same_placeholder() -> None:
    text = "Mario Rossi ha parlato con Mario Rossi."
    masked, mapping = mask_text(text)

    # "Mario Rossi" appears twice but should map to a single placeholder
    assert len(mapping) == 1


def test_masked_text_contains_no_original_pii() -> None:
    text = "Contatto: mario.rossi@example.com, tel. +39 02 1234567."
    masked, _ = mask_text(text)

    assert "mario.rossi@example.com" not in masked
    assert "+39 02 1234567" not in masked

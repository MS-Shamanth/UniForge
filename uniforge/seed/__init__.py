"""Seed vocabularies.

These are DERIVED reference tables, not the client's master data. UniForge makes no
compliance claim against files it was never given: every module reads a vocabulary
through `uniforge.vocab.Vocabulary`, which reports provenance per table
("supplied" when the real XLSX is dropped into data/in/, "seed" otherwise).

Swapping in the real 27k manufacturer list, 161k LOV and ~500-row UOM standard is a
data swap, not a rewrite.
"""

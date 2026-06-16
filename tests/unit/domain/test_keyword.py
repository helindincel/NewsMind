from __future__ import annotations

import pytest

from src.domain.value_objects.keyword import Keyword


class TestKeyword:
    def test_valid_keyword(self):
        kw = Keyword("climate change")
        assert kw.value == "climate change"

    def test_normalized_lowercases_and_strips(self):
        kw = Keyword("  Climate Change  ")
        assert kw.normalized() == "climate change"

    def test_str_returns_original_value(self):
        kw = Keyword("AI")
        assert str(kw) == "AI"

    def test_empty_keyword_raises(self):
        with pytest.raises(ValueError, match="empty"):
            Keyword("   ")

    def test_too_long_keyword_raises(self):
        with pytest.raises(ValueError, match="too long"):
            Keyword("a" * 101)

    def test_invalid_characters_raise(self):
        with pytest.raises(ValueError, match="invalid characters"):
            Keyword("climate<script>")

    def test_hyphens_allowed(self):
        kw = Keyword("state-of-the-art")
        assert kw.value == "state-of-the-art"

    def test_numbers_allowed(self):
        kw = Keyword("GPT4 model")
        assert kw.value == "GPT4 model"

    def test_keyword_is_immutable(self):
        kw = Keyword("test")
        with pytest.raises(Exception):
            kw.value = "changed"  # type: ignore[misc]

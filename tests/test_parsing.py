import pytest

from bot.parsing import positive_int


class TestPositiveInt:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("42", 42),
            (" 42 ", 42),
            ("1", 1),
            ("52428800", 52428800),
        ],
    )
    def test_parses_a_positive_number(self, value, expected):
        assert positive_int(value) == expected

    @pytest.mark.parametrize("value", [None, "", "   ", "abc", "1.5", "12x"])
    def test_rejects_anything_unparseable(self, value):
        assert positive_int(value) is None

    @pytest.mark.parametrize("value", ["0", "-1", "-52428800"])
    def test_rejects_zero_and_negatives(self, value):
        assert positive_int(value) is None

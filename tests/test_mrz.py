from datetime import date

import pytest

from uscis_autofill.mrz import MrzError, check_digit, parse_td3

# The synthetic specimen from ICAO Doc 9303 (a fictional person from the fictional state UTO).
L1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
L2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
TODAY = date(2026, 11, 11)


def test_icao_specimen_parses_and_every_check_digit_passes():
    mrz = parse_td3(L1, L2, today=TODAY)
    assert mrz.valid, mrz.checks
    assert (mrz.surname, mrz.given_names) == ("ERIKSSON", "ANNA MARIA")
    assert mrz.document_number == "L898902C3"
    assert mrz.nationality == "UTO" and mrz.issuing_country == "UTO"
    assert mrz.birth_date == date(1974, 8, 12)
    assert mrz.expiry_date == date(2012, 4, 15)
    assert mrz.sex == "F"
    assert mrz.name_possibly_truncated is False


def test_check_digit_known_values():
    assert check_digit("L898902C3") == 6
    assert check_digit("740812") == 2
    assert check_digit("120415") == 9


@pytest.mark.parametrize(
    "index, name",
    [(0, "document_number"), (13, "birth_date"), (21, "expiry_date"), (28, "personal_number")],
)
def test_a_changed_character_fails_the_matching_check(index, name):
    # Not every substitution is detectable: a mod-10 check misses any change that is a
    # multiple of 10 times the weight. These swaps are all caught.
    chars = list(L2)
    chars[index] = "0" if chars[index] != "0" else "1"
    mrz = parse_td3(L1, "".join(chars), today=TODAY)
    assert not mrz.valid
    assert mrz.checks[name] is False and mrz.checks["composite"] is False


def test_a_name_that_fills_the_field_is_flagged_as_possibly_cut_short():
    assert parse_td3("P<UTO" + "A" * 39, L2, today=TODAY).name_possibly_truncated is True


def test_birth_century_is_inferred_from_today():
    line2 = "L898902C36UTO3001012F1204159ZE184226B<<<<<10"
    assert parse_td3(L1, line2, today=date(2026, 1, 1)).birth_date == date(1930, 1, 1)
    assert parse_td3(L1, line2, today=date(2040, 1, 1)).birth_date == date(2030, 1, 1)


@pytest.mark.parametrize(
    "l1, l2",
    [(L1[:-1], L2), (L1, L2 + "<"), ("V" + L1[1:], L2), ("", "")],
)
def test_malformed_input_is_rejected(l1, l2):
    with pytest.raises(MrzError):
        parse_td3(l1, l2, today=TODAY)

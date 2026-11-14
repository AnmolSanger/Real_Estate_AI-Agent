from cities import INDIAN_CITIES, is_supported, to_location


def test_list_covers_the_census_cities():
    assert sum(len(cities) for cities in INDIAN_CITIES.values()) == 467
    assert len(INDIAN_CITIES) == 31


def test_telangana_is_split_from_andhra_pradesh():
    assert is_supported("Telangana", "Hyderabad")
    assert is_supported("Andhra Pradesh", "Visakhapatnam")
    assert not is_supported("Andhra Pradesh", "Hyderabad")


def test_current_names_replace_census_2011_names():
    assert is_supported("Haryana", "Gurugram")
    assert is_supported("Karnataka", "Bengaluru")
    assert not is_supported("Haryana", "Gurgaon")


def test_largest_city_comes_first():
    assert INDIAN_CITIES["Maharashtra"][0] == "Mumbai"
    assert INDIAN_CITIES["Uttar Pradesh"][0] == "Kanpur"


def test_no_city_appears_twice_in_a_state():
    for cities in INDIAN_CITIES.values():
        assert len(cities) == len(set(cities))


def test_location_includes_the_state_unless_they_match():
    assert to_location("Maharashtra", "Pune") == "Pune, Maharashtra"
    assert to_location("Delhi", "Delhi") == "Delhi"

from irb120_hito1.slider_controls import JOINT_SLIDERS, PRESETS_DEG, command_payload


def test_six_joint_specs_match_official_ranges() -> None:
    assert [(item.lower_deg, item.upper_deg) for item in JOINT_SLIDERS] == [
        (-165.0, 165.0),
        (-110.0, 110.0),
        (-110.0, 70.0),
        (-160.0, 160.0),
        (-120.0, 120.0),
        (-400.0, 400.0),
    ]


def test_command_payload_contains_exactly_six_joint_values() -> None:
    payload = command_payload(list(PRESETS_DEG["Prueba A"]))
    assert payload == list(PRESETS_DEG["Prueba A"])
    assert len(payload) == 6


def test_command_payload_clamps_out_of_range_values() -> None:
    assert command_payload([999.0] * 6) == [
        165.0,
        110.0,
        70.0,
        160.0,
        120.0,
        400.0,
    ]

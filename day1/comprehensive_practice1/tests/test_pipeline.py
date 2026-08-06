"""main_pipeline 모듈에 대한 pytest 테스트."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main_pipeline import CountryInfo, IPLocationInfo, WeatherItem, validate_weather


def test_weather_item_accepts_valid_range():
    item = WeatherItem.model_validate({"time": "2026-08-06T00:00", "temp": 25.0, "precip_prob": 50})
    assert item.temp == 25.0
    assert item.precip_prob == 50


def test_weather_item_rejects_precip_prob_over_100():
    with pytest.raises(ValidationError):
        WeatherItem.model_validate({"time": "2026-08-06T00:00", "temp": 25.0, "precip_prob": 150})


def test_validate_weather_filters_out_invalid_records():
    raw = [
        {"time": "2026-08-06T00:00", "temp": 25.0, "precip_prob": 30},
        {"time": "2026-08-06T01:00", "temp": 24.0, "precip_prob": 150},
    ]
    result = validate_weather(raw)
    assert len(result) == 1
    assert result[0].precip_prob == 30


def test_country_info_requires_two_letter_alpha2_code():
    with pytest.raises(ValidationError):
        CountryInfo.model_validate({"name": "South Korea", "alpha2_code": "KOR"})


def test_ip_location_info_parses_required_fields():
    info = IPLocationInfo.model_validate(
        {"ip": "8.8.8.8", "country": "United States", "city": "Ashburn", "isp": "Google LLC"}
    )
    assert info.ip == "8.8.8.8"

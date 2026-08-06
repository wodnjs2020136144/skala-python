"""Day1 종합 실습 1 — 데이터 수집 미니 파이프라인 
    작성자: 황재원(P345)
    작성일: 2026-08-06
    설명: 3개의 API를 비동기적으로 호출하여 데이터를 수집하는 미니 파이프라인
"""
import asyncio
import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia/Seoul"
)
COUNTRY_URL = "https://countries.dev/alpha/KOR"
IP_URL = "http://ip-api.com/json/8.8.8.8"

HTTP_TIMEOUT_SECONDS = 10.0

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("MiniPipeline")

# ---------------------------------------------------------
# 1. Pydantic v2 스키마 정의 (Step 3)
# ---------------------------------------------------------


class WeatherItem(BaseModel):
    """Open-Meteo 시간대별 기온/강수확률 레코드."""

    time_str: str = Field(..., alias="time")
    temp: float = Field(..., description="기온(섭씨)")
    precip_prob: float = Field(..., ge=0, le=100, description="강수확률(0~100%)")


class CountryInfo(BaseModel):
    """Countries.dev 국가 기본 정보."""

    name: str = Field(..., description="국가명")
    alpha2_code: str = Field(..., min_length=2,
                             max_length=2, description="국가 코드")


class IPLocationInfo(BaseModel):
    """ip-api IP 위치 정보."""

    ip: str = Field(..., description="조회 IP")
    country: str = Field(..., description="국가")
    city: str = Field(..., description="도시")
    isp: str = Field(..., description="ISP 제공자")

# ---------------------------------------------------------
# 2. 비동기 수집 모듈 — asyncio + httpx (Step 2)
# ---------------------------------------------------------


async def fetch_weather(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """Open-Meteo API에서 서울 시간대별 기온/강수확률을 수집한다."""
    logger.info("Open-Meteo 날씨 API 수집 시작...")
    resp = await client.get(WEATHER_URL, timeout=HTTP_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    probs = hourly.get("precipitation_probability", [])

    result = [
        {"time": t, "temp": temp, "precip_prob": prob}
        for t, temp, prob in zip(times, temps, probs, strict=True)
    ]
    logger.info(f"Open-Meteo 수집 완료 ({len(result)}건)")
    return result


async def fetch_country(client: httpx.AsyncClient) -> dict[str, Any]:
    """Countries.dev API에서 대한민국 국가 정보를 수집한다."""
    logger.info("Countries.dev 국가 정보 API 수집 시작...")
    resp = await client.get(COUNTRY_URL, timeout=HTTP_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    return {"name": data["name"], "alpha2_code": data["alpha2Code"]}


async def fetch_ip_info(client: httpx.AsyncClient) -> dict[str, Any]:
    """ip-api API에서 8.8.8.8의 지리적 위치 정보를 수집한다."""
    logger.info("ip-api IP 위치 정보 수집 시작...")
    resp = await client.get(IP_URL, timeout=HTTP_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    return {
        "ip": data["query"],
        "country": data["country"],
        "city": data["city"],
        "isp": data["isp"],
    }


async def collect_all_data() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """3개 API를 asyncio.gather로 동시 수집한다."""
    async with httpx.AsyncClient() as client:
        start_time = time.perf_counter()
        weather_res, country_res, ip_res = await asyncio.gather(
            fetch_weather(client),
            fetch_country(client),
            fetch_ip_info(client),
        )
        elapsed = time.perf_counter() - start_time
        logger.info(f"3개 API 비동기 동시 수집 완료 (소요시간: {elapsed:.3f}초)")
        return weather_res, country_res, ip_res


if __name__ == "__main__":
    weather_raw, country_raw, ip_raw = asyncio.run(collect_all_data())

    valid_weather = []
    for item in weather_raw:
        try:
            valid_weather.append(WeatherItem.model_validate(item))
        except ValidationError as ve:
            logger.error(f"Weather 검증 실패: {ve}")

    country_info = CountryInfo.model_validate(country_raw)
    ip_info = IPLocationInfo.model_validate(ip_raw)

    logger.info(
        f"Pydantic 검증 완료 - Weather: {len(valid_weather)}건, "
        f"Country: {country_info.name}, IP: {ip_info.ip}"
    )
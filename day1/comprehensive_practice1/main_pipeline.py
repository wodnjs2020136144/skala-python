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

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia/Seoul"
)
COUNTRY_URL = "https://countries.dev/alpha/KOR"
IP_URL = "http://ip-api.com/json/8.8.8.8"

HTTP_TIMEOUT_SECONDS = 10.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("MiniPipeline")

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
    weather, country, ip = asyncio.run(collect_all_data())
    logger.info(f"날씨 데이터: {weather[:3]} ...")
    logger.info(f"국가 정보: {country}")
    logger.info(f"IP 위치 정보: {ip}")
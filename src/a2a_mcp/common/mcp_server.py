# type: ignore
"""
MCP 服务：Agent Card 注册表 + 供任务 Agent 使用的工具。

- 从 agent_cards/*.json 加载 agent card，用 OpenAI 兼容 API 生成嵌入。
- 暴露资源：resource://agent_cards/list、resource://agent_cards/{card_name}。
- 工具：
  - find_agent(query)
  - get_travel_schema()
  - get_travel_inventory()
  - search_flights(origin, destination, ticket_class, limit)
  - search_hotels(city, hotel_type, room_type, limit)
  - search_rental_cars(city, type_of_car, limit)
  - query_travel_data(SQL)
  - query_places_data(query)
"""
import json
import os
import re
import sqlite3
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from a2a_mcp.common.utils import get_llm_model, init_api_key
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger


logger = get_logger(__name__)
AGENT_CARDS_DIR = "agent_cards"
MODEL = "BAAI/bge-large-en-v1.5"  # 嵌入模型（OpenAI 兼容端点）
SQLLITE_DB = "travel_agency.db"
DEFAULT_RESULT_LIMIT = 10
MAX_RESULT_LIMIT = 50

CITY_AIRPORT_ALIASES = {
    "beijing": ["PEK", "PKX"],
    "北京": ["PEK", "PKX"],
    "london": ["LHR", "LGW", "STN"],
    "伦敦": ["LHR", "LGW", "STN"],
    "jinan": ["TNA"],
    "济南": ["TNA"],
    "shanghai": ["PVG", "SHA"],
    "上海": ["PVG", "SHA"],
    "qingdao": ["TAO"],
    "青岛": ["TAO"],
    "san francisco": ["SFO"],
    "sfo": ["SFO"],
    "new york": ["JFK"],
    "tokyo": ["HND"],
    "singapore": ["SIN"],
    "dubai": ["DXB"],
    "paris": ["CDG"],
    "frankfurt": ["FRA"],
    "munich": ["MUC"],
    "seoul": ["ICN"],
    "hong kong": ["HKG"],
}

TRAVEL_SCHEMA = {
    "flights": {
        "columns": [
            "id",
            "carrier",
            "flight_number",
            "from_airport",
            "to_airport",
            "ticket_class",
            "price",
        ],
        "notes": [
            "Flights are stored by airport code, not city name.",
            "Use search_flights when the user gives city names or mixed natural language.",
            "query_travel_data is available as a fallback for custom SELECT queries.",
        ],
    },
    "hotels": {
        "columns": [
            "id",
            "name",
            "city",
            "hotel_type",
            "room_type",
            "price_per_night",
        ],
        "notes": [
            "There are no columns for breakfast, star rating, safety, or subway proximity.",
            "Choose among SQL results using natural-language reasoning for those soft preferences.",
        ],
    },
    "rental_cars": {
        "columns": [
            "id",
            "provider",
            "city",
            "type_of_car",
            "daily_rate",
        ],
        "notes": [
            "Rental cars are stored by city name.",
        ],
    },
}


def generate_embeddings(text: str) -> list[float]:
    """使用 OpenAI 兼容的嵌入 API 为文本生成嵌入向量。"""
    client = init_api_key()
    response = client.embeddings.create(model=MODEL, input=text)
    return response.data[0].embedding


def load_agent_cards() -> tuple[list[str], list[dict]]:
    """从 AGENT_CARDS_DIR 加载 agent card JSON 文件；返回 (card_uris, agent_cards)。"""
    card_uris: list[str] = []
    agent_cards: list[dict] = []
    dir_path = Path(AGENT_CARDS_DIR)
    if not dir_path.is_dir():
        logger.error(
            "Agent cards directory not found or is not a directory: %s",
            AGENT_CARDS_DIR,
        )
        return card_uris, agent_cards

    logger.info("Loading agent cards from card repo: %s", AGENT_CARDS_DIR)

    for filename in os.listdir(AGENT_CARDS_DIR):
        if not filename.lower().endswith(".json"):
            continue

        file_path = dir_path / filename
        if not file_path.is_file():
            continue

        logger.info("Reading file: %s", filename)
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            card_uris.append(f"resource://agent_cards/{Path(filename).stem}")
            agent_cards.append(data)
        except json.JSONDecodeError as jde:
            logger.error("JSON Decoder Error %s", jde)
        except OSError as e:
            logger.error("Error reading file %s: %s", filename, e)
        except Exception as e:
            logger.error(
                "An unexpected error occurred processing %s: %s",
                filename,
                e,
                exc_info=True,
            )

    logger.info("Finished loading agent cards. Found %d cards.", len(agent_cards))
    return card_uris, agent_cards


def build_agent_card_embeddings(
    card_uris: list[str] | None = None,
    agent_cards: list[dict] | None = None,
) -> pd.DataFrame | None:
    """加载 agent card，为每张卡计算嵌入，返回含 card_uri、agent_card、card_embeddings 的 DataFrame。"""
    if card_uris is None or agent_cards is None:
        card_uris, agent_cards = load_agent_cards()
    logger.info("Generating Embeddings for agent cards")
    try:
        if agent_cards:
            df = pd.DataFrame({"card_uri": card_uris, "agent_card": agent_cards})
            df["card_embeddings"] = df.apply(
                lambda row: generate_embeddings(json.dumps(row["agent_card"])),
                axis=1,
            )
            return df
        logger.info("Done generating embeddings for agent cards")
        return None
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e, exc_info=True)
        return None


def _normalize_limit(limit: int | None) -> int:
    try:
        value = int(limit or DEFAULT_RESULT_LIMIT)
    except (TypeError, ValueError):
        value = DEFAULT_RESULT_LIMIT
    return max(1, min(value, MAX_RESULT_LIMIT))


def _fetch_rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with sqlite3.connect(SQLLITE_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def _distinct_values(table: str, column: str) -> list[str]:
    rows = _fetch_rows(
        f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
    )
    return [str(row[column]) for row in rows]


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_airport_codes(value: str, available_codes: set[str]) -> list[str]:
    if not value:
        return []

    raw = str(value).strip()
    if not raw:
        return []

    upper = raw.upper()
    explicit_codes = [
        match.group(0)
        for match in re.finditer(r"\b[A-Z]{3}\b", upper)
        if match.group(0) in available_codes
    ]
    if explicit_codes:
        return _dedupe_keep_order(explicit_codes)

    if upper in available_codes:
        return [upper]

    normalized = raw.casefold()
    alias_codes: list[str] = []
    for alias, codes in CITY_AIRPORT_ALIASES.items():
        if alias.casefold() in normalized:
            alias_codes.extend([code for code in codes if code in available_codes])
    return _dedupe_keep_order(alias_codes)


def _normalize_hotel_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    mapping = {
        "HOTEL": "HOTEL",
        "AIRBNB": "AIRBNB",
        "PRIVATE": "PRIVATE",
        "PRIVATE_PROPERTY": "PRIVATE",
    }
    return mapping.get(cleaned)


def _normalize_room_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    allowed = {"STANDARD", "SINGLE", "DOUBLE", "SUITE"}
    return cleaned if cleaned in allowed else None


def _normalize_car_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    allowed = {"SEDAN", "SUV", "TRUCK"}
    return cleaned if cleaned in allowed else None


def get_travel_inventory_data() -> dict[str, Any]:
    flight_codes = sorted(
        set(_distinct_values("flights", "from_airport"))
        | set(_distinct_values("flights", "to_airport"))
    )
    return {
        "database": SQLLITE_DB,
        "flights": {
            "airport_codes": flight_codes,
            "ticket_classes": _distinct_values("flights", "ticket_class"),
        },
        "hotels": {
            "cities": _distinct_values("hotels", "city"),
            "hotel_types": _distinct_values("hotels", "hotel_type"),
            "room_types": _distinct_values("hotels", "room_type"),
        },
        "rental_cars": {
            "cities": _distinct_values("rental_cars", "city"),
            "type_of_car": _distinct_values("rental_cars", "type_of_car"),
        },
    }


def get_travel_schema_data() -> dict[str, Any]:
    inventory = get_travel_inventory_data()
    return {
        "database": SQLLITE_DB,
        "tables": TRAVEL_SCHEMA,
        "inventory": inventory,
        "sample_queries": {
            "flights": "SELECT carrier, flight_number, from_airport, to_airport, ticket_class, price FROM flights WHERE from_airport = 'TNA' AND to_airport = 'PEK' AND ticket_class = 'ECONOMY'",
            "hotels": "SELECT name, city, hotel_type, room_type, price_per_night FROM hotels WHERE city = 'Beijing' AND hotel_type = 'HOTEL' AND room_type = 'SUITE'",
            "rental_cars": "SELECT provider, city, type_of_car, daily_rate FROM rental_cars WHERE city = 'Beijing' AND type_of_car = 'SEDAN'",
        },
    }


def search_flights_data(
    origin: str,
    destination: str,
    ticket_class: str | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> dict[str, Any]:
    inventory = get_travel_inventory_data()
    available_codes = set(inventory["flights"]["airport_codes"])
    resolved_origin = _normalize_airport_codes(origin, available_codes)
    resolved_destination = _normalize_airport_codes(destination, available_codes)
    normalized_class = str(ticket_class).strip().upper() if ticket_class else None
    allowed_classes = set(inventory["flights"]["ticket_classes"])

    if not resolved_origin:
        return {
            "error": "Could not resolve origin to supported airport code(s).",
            "origin": origin,
            "available_airport_codes": inventory["flights"]["airport_codes"],
        }
    if not resolved_destination:
        return {
            "error": "Could not resolve destination to supported airport code(s).",
            "destination": destination,
            "available_airport_codes": inventory["flights"]["airport_codes"],
        }
    if normalized_class and normalized_class not in allowed_classes:
        return {
            "error": "Unsupported ticket_class.",
            "ticket_class": ticket_class,
            "allowed_ticket_classes": inventory["flights"]["ticket_classes"],
        }

    placeholders_from = ",".join("?" for _ in resolved_origin)
    placeholders_to = ",".join("?" for _ in resolved_destination)
    params: list[Any] = [*resolved_origin, *resolved_destination]
    sql = f"""
        SELECT carrier, flight_number, from_airport, to_airport, ticket_class, price
        FROM flights
        WHERE from_airport IN ({placeholders_from})
          AND to_airport IN ({placeholders_to})
    """
    if normalized_class:
        sql += " AND ticket_class = ?"
        params.append(normalized_class)
    sql += " ORDER BY price ASC, carrier ASC LIMIT ?"
    params.append(_normalize_limit(limit))

    return {
        "criteria": {
            "origin_input": origin,
            "destination_input": destination,
            "resolved_origin_codes": resolved_origin,
            "resolved_destination_codes": resolved_destination,
            "ticket_class": normalized_class,
        },
        "results": _fetch_rows(sql, tuple(params)),
    }


def search_hotels_data(
    city: str,
    hotel_type: str | None = None,
    room_type: str | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> dict[str, Any]:
    normalized_hotel_type = _normalize_hotel_type(hotel_type)
    normalized_room_type = _normalize_room_type(room_type)
    params: list[Any] = [str(city).strip()]
    sql = """
        SELECT name, city, hotel_type, room_type, price_per_night
        FROM hotels
        WHERE lower(city) = lower(?)
    """
    if hotel_type and normalized_hotel_type is None:
        return {
            "error": "Unsupported hotel_type.",
            "hotel_type": hotel_type,
            "allowed_hotel_types": get_travel_inventory_data()["hotels"]["hotel_types"],
        }
    if room_type and normalized_room_type is None:
        return {
            "error": "Unsupported room_type.",
            "room_type": room_type,
            "allowed_room_types": get_travel_inventory_data()["hotels"]["room_types"],
        }
    if normalized_hotel_type:
        sql += " AND hotel_type = ?"
        params.append(normalized_hotel_type)
    if normalized_room_type:
        sql += " AND room_type = ?"
        params.append(normalized_room_type)
    sql += " ORDER BY price_per_night ASC, name ASC LIMIT ?"
    params.append(_normalize_limit(limit))

    return {
        "criteria": {
            "city": city,
            "hotel_type": normalized_hotel_type,
            "room_type": normalized_room_type,
        },
        "results": _fetch_rows(sql, tuple(params)),
    }


def search_rental_cars_data(
    city: str,
    type_of_car: str | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> dict[str, Any]:
    normalized_car_type = _normalize_car_type(type_of_car)
    if type_of_car and normalized_car_type is None:
        return {
            "error": "Unsupported type_of_car.",
            "type_of_car": type_of_car,
            "allowed_type_of_car": get_travel_inventory_data()["rental_cars"]["type_of_car"],
        }

    params: list[Any] = [str(city).strip()]
    sql = """
        SELECT provider, city, type_of_car, daily_rate
        FROM rental_cars
        WHERE lower(city) = lower(?)
    """
    if normalized_car_type:
        sql += " AND type_of_car = ?"
        params.append(normalized_car_type)
    sql += " ORDER BY daily_rate ASC, provider ASC LIMIT ?"
    params.append(_normalize_limit(limit))

    return {
        "criteria": {
            "city": city,
            "type_of_car": normalized_car_type,
        },
        "results": _fetch_rows(sql, tuple(params)),
    }


def query_travel_data_sql(query: str) -> dict[str, Any]:
    logger.info("Query sqllite : %s", query)
    if not query or not query.strip():
        return {"error": "Query cannot be empty."}

    normalized = query.strip().rstrip(";")
    if not normalized.upper().startswith("SELECT"):
        return {"error": f"Only SELECT queries are allowed, got: {query}"}

    try:
        rows = _fetch_rows(normalized)
        return {
            "query": normalized,
            "row_count": len(rows),
            "results": rows,
        }
    except Exception as e:
        logger.error("Exception running query %s", e)
        logger.error(traceback.format_exc())
        err_msg = str(e)
        hint = (
            "Use get_travel_schema/get_travel_inventory/search_flights/search_hotels/"
            "search_rental_cars to inspect supported fields before retrying."
        )
        return {
            "error": err_msg,
            "query": normalized,
            "hint": hint,
        }


def serve(host, port, transport):  # noqa: PLR0915
    """初始化并运行 Agent Cards MCP 服务。"""
    logger.info("Starting Agent Cards MCP Server")
    mcp = FastMCP("agent-cards", host=host, port=port)

    card_uris, agent_cards = load_agent_cards()
    embeddings_df: pd.DataFrame | None = None

    def ensure_embeddings_df() -> pd.DataFrame | None:
        nonlocal embeddings_df
        if embeddings_df is not None:
            return embeddings_df
        if not agent_cards:
            return None
        try:
            embeddings_df = build_agent_card_embeddings(card_uris, agent_cards)
            return embeddings_df
        except Exception as e:
            logger.error("Failed to initialize agent card embeddings: %s", e, exc_info=True)
            return None

    @mcp.tool(
        name="find_agent",
        description="根据自然语言查询字符串找到最相关的 agent card。",
    )
    def find_agent(query: str) -> str:
        df = ensure_embeddings_df()
        if df is None or len(df) == 0:
            logger.warning("find_agent: no agent cards loaded")
            return json.dumps(
                {
                    "error": (
                        "find_agent is unavailable. Check agent_cards, embedding initialization, "
                        "and OPENAI/OpenAI-compatible configuration."
                    )
                }
            )

        try:
            client = init_api_key()
            query_embedding = client.embeddings.create(
                model=MODEL,
                input=query,
            ).data[0].embedding
        except Exception as e:
            logger.error("find_agent embedding request failed: %s", e, exc_info=True)
            return json.dumps(
                {
                    "error": (
                        "find_agent requires a working OPENAI_API_KEY/OPENAI_BASE_URL "
                        "and embedding endpoint."
                    )
                }
            )

        dot_products = np.dot(np.stack(df["card_embeddings"]), query_embedding)
        best_match_index = int(np.argmax(dot_products))
        logger.debug(
            "Found best match at index %s with score %s",
            best_match_index,
            float(dot_products[best_match_index]),
        )
        agent_card = df.iloc[best_match_index]["agent_card"]
        return (
            json.dumps(agent_card, ensure_ascii=False)
            if isinstance(agent_card, dict)
            else str(agent_card)
        )

    @mcp.tool(
        description="Return the SQLite schema, supported columns, and sample queries for flights/hotels/rental cars.",
    )
    def get_travel_schema() -> dict[str, Any]:
        return get_travel_schema_data()

    @mcp.tool(
        description="Return supported flight airport codes, ticket classes, hotel cities/types/room types, and rental-car cities/types.",
    )
    def get_travel_inventory() -> dict[str, Any]:
        return get_travel_inventory_data()

    @mcp.tool(
        description="Search flights using airport codes or city names. Prefer this over handwritten SQL when possible.",
    )
    def search_flights(
        origin: str,
        destination: str,
        ticket_class: str | None = None,
        limit: int = DEFAULT_RESULT_LIMIT,
    ) -> dict[str, Any]:
        return search_flights_data(origin, destination, ticket_class, limit)

    @mcp.tool(
        description="Search hotels by city, hotel type, and room type. Prefer this over handwritten SQL when possible.",
    )
    def search_hotels(
        city: str,
        hotel_type: str | None = None,
        room_type: str | None = None,
        limit: int = DEFAULT_RESULT_LIMIT,
    ) -> dict[str, Any]:
        return search_hotels_data(city, hotel_type, room_type, limit)

    @mcp.tool(
        description="Search rental cars by city and car type. Prefer this over handwritten SQL when possible.",
    )
    def search_rental_cars(
        city: str,
        type_of_car: str | None = None,
        limit: int = DEFAULT_RESULT_LIMIT,
    ) -> dict[str, Any]:
        return search_rental_cars_data(city, type_of_car, limit)

    @mcp.tool()
    def query_places_data(query: str):
        """使用 OpenAI API 查询地点（替代 Google Places）。"""
        logger.info("Search for places: %s", query)
        client = init_api_key()
        prompt = f"""
        You are a helpful assistant that provides information about places.
        Given a natural language query, return a JSON array of at most 10 places.
        Each place should have the fields: "name", "address", "category".
        Example output:
        [
            {{"name": "Central Park", "address": "New York, NY, USA", "category": "park"}},
            {{"name": "Statue of Liberty", "address": "New York, NY, USA", "category": "monument"}}
        ]
        Query: "{query}"
        Return strictly valid JSON.
        """
        try:
            response = client.chat.completions.create(
                model=get_llm_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            content = response.choices[0].message.content
            places = json.loads(content)
            return {"places": places}
        except json.JSONDecodeError:
            logger.info("Failed to decode JSON from OpenAI response: %s", content)
            return {"places": []}
        except Exception as e:
            logger.info("OpenAI API error: %s", e)
            return {"places": []}

    @mcp.tool()
    def query_travel_data(query: str) -> dict[str, Any]:
        return query_travel_data_sql(query)

    @mcp.resource("resource://agent_cards/list", mime_type="application/json")
    def get_agent_cards() -> dict:
        resources: dict[str, list[str]] = {}
        logger.info("Starting read resources")
        if not card_uris:
            resources["agent_cards"] = []
            return resources
        resources["agent_cards"] = card_uris
        return resources

    @mcp.resource(
        "resource://agent_cards/{card_name}", mime_type="application/json"
    )
    def get_agent_card(card_name: str) -> dict:
        resources: dict[str, list[dict]] = {}
        logger.info(
            "Starting read resource resource://agent_cards/%s",
            card_name,
        )
        if not agent_cards:
            resources["agent_card"] = []
            return resources
        target_uri = f"resource://agent_cards/{card_name}"
        resources["agent_card"] = [
            card
            for uri, card in zip(card_uris, agent_cards)
            if uri == target_uri
        ]
        return resources

    logger.info(
        "Agent cards MCP Server at %s:%s and transport %s",
        host,
        port,
        transport,
    )
    mcp.run(transport=transport)


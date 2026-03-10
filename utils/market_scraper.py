import requests
import datetime
from datetime import timedelta
from utils.db_manager import DatabaseManager
import threading

BASE_URL = "https://api.agmarknet.gov.in/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
}
VARIETY = "[100007]"


def safe_strip(value):
    """Safely strips a string, handling None or non-string types."""
    if value is None:
        return ""
    return str(value).strip()


def get_dynamic_dates():
    today = datetime.date.today()
    week_ago = today - timedelta(days=7)
    return week_ago.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def fetch_page_data(url):
    """Helper to fetch a single page"""
    try:
        resp = requests.get(url, headers=HEADERS)
        json_data = resp.json()

        if not json_data.get("data") or not json_data["data"].get("records"):
            return [], None

        records_obj = json_data["data"]["records"][0]
        data_list = records_obj.get("data", [])
        pagination_list = records_obj.get("pagination", [])
        pagination_info = pagination_list[0] if pagination_list else None

        return data_list, pagination_info
    except Exception as e:
        print(f"Error fetching page: {e}")
        return [], None


def fetch_commodities_for_group(group_id, all_commodities_list, lock):
    """Worker function to fetch commodities for a single group."""
    if group_id == 99999:
        return

    try:
        cmdt_url = f"{BASE_URL}/all-type-report/commodity-filter?group=[{group_id}]"
        cmdt_resp = requests.get(cmdt_url, headers=HEADERS)
        items = cmdt_resp.json().get("data", [])

        if isinstance(items, list):
            new_commodities = []
            for item in items:
                c_name = safe_strip(item.get("cmdt_name"))
                c_id = item.get("id")
                if c_name and c_id:
                    new_commodities.append((group_id, c_id, c_name))
            
            with lock:
                all_commodities_list.extend(new_commodities)
                print(".", end="", flush=True)
    except Exception as e:
        pass


def init_cache_db():
    """
    Creates tables and performs ONE-TIME population of ALL
    commodities and location data if tables are empty.
    """
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM api_cached_locations")
    if cursor.fetchone()[0] == 0:
        print("Location cache empty. Fetching ALL locations from Agmarknet...")
        try:
            url = f"{BASE_URL}/market-district-state"
            resp = requests.get(url, headers=HEADERS)
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                data = data["data"]

            records = []
            for entry in data:
                records.append(
                    (
                        entry.get("state_id"),
                        safe_strip(entry.get("state_name")),
                        entry.get("district_id"),
                        safe_strip(entry.get("district_name")),
                        entry.get("market_id"),
                        safe_strip(entry.get("market_name")),
                    )
                )

            cursor.executemany(
                """
                INSERT INTO api_cached_locations 
                (state_id, state_name, district_id, district_name, market_id, market_name)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()
            print(f"Cached {len(records)} locations.")
        except Exception as e:
            print(f"Error fetching locations: {e}")

    cursor.execute("SELECT count(*) FROM api_cached_commodities")
    if cursor.fetchone()[0] == 0:
        print("Commodity cache empty. Scraping All commodities...")
        try:
            group_url = f"{BASE_URL}/all-type-report/commoditygroup-filter"
            resp = requests.get(group_url, headers=HEADERS)
            groups = resp.json().get("data", [])

            all_commodities = []
            threads = []
            lock = threading.Lock()

            print(f"Scanning {len(groups)} groups...", end=" ", flush=True)

            for group in groups:
                group_id = group["id"]
                
                thread = threading.Thread(
                    target=fetch_commodities_for_group, 
                    args=(group_id, all_commodities, lock)
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()


            cursor.executemany(
                """
                INSERT OR IGNORE INTO api_cached_commodities (group_id, commodity_id, commodity_name)
                VALUES (?, ?, ?)
                """,
                all_commodities,
            )
            conn.commit()
            print(f"Cached {len(all_commodities)} commodities")

        except Exception as e:
            print(f"Error fetching commodities: {e}")

    conn.close()


def calculate_trend(
    data_points, commodity_name, state_name, district_name, market_name
):
    """
    Calculates trend metrics and generates detailed price history list.
    """
    prices_only = [d["price"] for d in data_points]
    count = len(prices_only)

    trend_overall = "stable"
    percentage_change = 0.0
    latest_price = 0
    avg_price = 0
    highest_price = 0
    lowest_price = 0
    detailed_prices = []

    if count > 0:
        latest_price = prices_only[-1]
        highest_price = max(prices_only)
        lowest_price = min(prices_only)
        avg_price = round(sum(prices_only) / count, 2)

        if count > 1 and prices_only[0] != 0:
            first_price = prices_only[0]
            price_change = latest_price - first_price
            if price_change > 0:
                trend_overall = "upward"
            elif price_change < 0:
                trend_overall = "downward"
            percentage_change = (price_change / first_price) * 100

        for i, point in enumerate(data_points):
            current_price = point["price"]
            date_str = point["date"].strftime("%Y-%m-%d")
            step_trend = "stable"
            if i > 0:
                prev_price = data_points[i - 1]["price"]
                if current_price > prev_price:
                    step_trend = "up"
                elif current_price < prev_price:
                    step_trend = "down"

            detailed_prices.append(
                {"date": date_str, "price": current_price, "trend": step_trend}
            )

    return {
        "commodity": commodity_name,
        "state": state_name,
        "district": district_name,
        "market": market_name,
        "latest_price": latest_price,
        "trend": trend_overall,
        "percentage_change": round(percentage_change, 2),
        "data_points_found": count,
        "average_price": avg_price,
        "highest_price": highest_price,
        "lowest_price": lowest_price,
        "prices": detailed_prices,
    }


def fetch_live_market_data(commodity, state, district=None):
    """
    1. Looks up Commodity & State IDs from SQLite
    2. Fetches Live Price Data from Agmarknet
    3. Returns Processed Trend JSON
    """

    from_date, to_date = get_dynamic_dates()

    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT group_id, commodity_id, commodity_name 
        FROM api_cached_commodities 
        WHERE commodity_name LIKE ? 
        ORDER BY LENGTH(commodity_name) ASC 
        LIMIT 1
        """,
        (f"%{commodity}%",),
    )
    cmdt_row = cursor.fetchone()

    if not cmdt_row:
        conn.close()
        return {
            "error": f'Commodity "{commodity}" not found in database'
        }

    group_id = cmdt_row["group_id"]
    cmdt_id = cmdt_row["commodity_id"]
    official_commodity_name = cmdt_row["commodity_name"]

    cursor.execute(
        """
        SELECT state_id, state_name 
        FROM api_cached_locations 
        WHERE state_name LIKE ? 
        ORDER BY LENGTH(state_name) ASC
        LIMIT 1
        """,
        (f"%{state}%",),
    )
    state_row = cursor.fetchone()

    conn.close()

    if not state_row:
        return {"error": f'State "{state}" not found in database'}

    state_id = state_row["state_id"]
    official_state_name = state_row["state_name"]

    base_query = (
        f"{BASE_URL}/daily-price-arrival/report?"
        f"from_date={from_date}&"
        f"to_date={to_date}&"
        f"group={group_id}&"
        f"commodity={cmdt_id}&"
        f"state={state_id}&"
        f"variety={VARIETY}"
    )

    all_raw_records = []
    current_page = 1
    total_pages = 1

    while current_page <= total_pages:
        page_url = f"{base_query}&page_no={current_page}"
        records, pag_info = fetch_page_data(page_url)

        if records:
            all_raw_records.extend(records)
            if current_page == 1 and pag_info:
                total_pages = pag_info.get("total_pages", 1)
        else:
            break
        current_page += 1

    if not all_raw_records:
        return {"error": "No data records found from API for the last 7 days"}

    processed_data = []

    for record in all_raw_records:
        try:
            rec_district = record.get("district_name", "")

            if (
                district
                and safe_strip(district).lower() not in safe_strip(rec_district).lower()
            ):
                continue

            rec_market = record.get("market_name", "Unknown Market")

            date_str = record.get("arrival_date", "")
            date_obj = datetime.datetime.strptime(date_str, "%d-%m-%Y")

            price_str = record.get("model_price", "0").replace(",", "")
            price = float(price_str)

            processed_data.append(
                {
                    "date": date_obj,
                    "price": price,
                    "market": rec_market,
                    "district": rec_district,
                }
            )

        except (ValueError, KeyError):
            continue

    if not processed_data:
        msg = (
            f'No data found for district "{district}"'
            if district
            else "No data found after processing"
        )
        return {"error": msg}

    processed_data.sort(key=lambda x: x["date"])

    latest_record = processed_data[-1]
    final_market_name = latest_record["market"]
    final_district_name = latest_record["district"]

    result = calculate_trend(
        data_points=processed_data,
        commodity_name=official_commodity_name,
        state_name=official_state_name,
        district_name=final_district_name,
        market_name=final_market_name,
    )

    return result


init_cache_db()
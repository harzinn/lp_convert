import requests
from concurrent.futures import ThreadPoolExecutor

def fetch_item_name(esi_base_url, item_id):
    try:
        response = requests.get(f"{esi_base_url}/v3/universe/types/{item_id}/")
        response.raise_for_status()
        item_data = response.json()
        return item_id, item_data['name']
    except requests.RequestException as e:
        print(f"Error fetching item name for item ID {item_id}: {e}")
        return item_id, f"Unknown-{item_id}"

def fetch_market_data(esi_base_url, market_orders_url, region_id, item_id):
    try:
        response = requests.get(f"{esi_base_url}{market_orders_url}{region_id}/orders/?datasource=tranquility&order_type=sell&type_id={item_id}")
        response.raise_for_status()
        market_data = response.json()
        sell_orders = [order for order in market_data if not order['is_buy_order']]
        return item_id, sell_orders
    except requests.RequestException as e:
        print(f"Error fetching market data for item ID {item_id}: {e}")
        return item_id, []

def get_best_isk_to_lp_ratio():
    # API Endpoints
    esi_base_url = "https://esi.evetech.net"
    lp_store_url = "/v1/loyalty/stores/"
    market_orders_url = "/v1/markets/"
    region_id = 10000002  # The Forge region ID
    npc_corp_id = 1000002  # Example NPC Corporation ID

    try:
        print("Fetching LP store data...")
        lp_store_response = requests.get(f"{esi_base_url}{lp_store_url}{npc_corp_id}/offers/")
        lp_store_response.raise_for_status()
        lp_store_data = lp_store_response.json()
        print("LP store data fetched successfully.")

        # Process LP store data
        items_lp = {offer['type_id']: offer['lp_cost'] for offer in lp_store_data if 'type_id' in offer and 'lp_cost' in offer}
        print(f"Processing {len(items_lp)} items from LP store...")

        # Fetch item names
        with ThreadPoolExecutor(max_workers=10) as executor:
            name_futures = [executor.submit(fetch_item_name, esi_base_url, item_id) for item_id in items_lp.keys()]
            item_names = {item_id: name for item_id, name in [future.result() for future in name_futures]}

        # Fetch market data and calculate ISK to LP ratios
        with ThreadPoolExecutor(max_workers=10) as executor:
            market_futures = [executor.submit(fetch_market_data, esi_base_url, market_orders_url, region_id, item_id) for item_id in items_lp.keys()]
            
            best_ratios = {}
            for future in market_futures:
                item_id, sell_orders = future.result()
                if sell_orders:
                    max_price = max(sell_orders, key=lambda x: x['price'])['price']
                    isk_to_lp_ratio = max_price / items_lp[item_id]
                    best_ratios[item_id] = isk_to_lp_ratio
                    print(f"{item_names[item_id]} (ID: {item_id}): Best ISK to LP ratio calculated.")

        # Sort items by best ISK to LP ratio
        sorted_best_ratios = sorted(best_ratios.items(), key=lambda x: x[1], reverse=True)
        print("\nSorting items by best ISK to LP ratio...\n")
        return [(item_names[item_id], ratio) for item_id, ratio in sorted_best_ratios]

    except requests.RequestException as e:
        return f"An error occurred: {e}"

# Running the function
best_value_items = get_best_isk_to_lp_ratio()
print("Best Value Items (ISK to LP Ratio):\n")
for item_name, ratio in best_value_items:
    print(f"{item_name:30} - Ratio: {ratio:.2f}")


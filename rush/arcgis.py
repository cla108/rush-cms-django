import requests

def get_max_record_count(layer_url: str) -> int:

    metadata_url = f"{layer_url}?f=json"

    response = requests.get(metadata_url)
    response.raise_for_status()

    data = response.json()

    if "maxRecordCount" not in data:
        raise ValueError("maxRecordCount not found in ArcGIS metadata.")

    return data["maxRecordCount"]



def fetch_all_features(layer_url: str) -> dict:

    max_record_count = get_max_record_count(layer_url)

    offset = 0
    all_features= []

    while True:
        query_url = (
            f"{layer_url}/query"
            f"?where=1=1"
            f"&outFields=*"
            f"&returnGeometry=true"
            f"&f=geojson"
            f"&resultOffset={offset}"
            f"&resultRecordCount={max_record_count}"
        )

        response = requests.get(query_url)
        response.raise_for_status()

        data = response.json()
        features = data.get("features", [])

        all_features.extend(features)

        if len(features) < max_record_count:
            break
        
        offset += max_record_count
    
    return {
        "type": "FeatureCollection",
        "features": all_features,
    }
import requests
from time import gmtime, strftime
from typing import Any, Dict, List
from pathlib import Path

# API Details
#TODO: Replace API key below
API_KEY = "<REPLACE ME>"

# Constants
API_URL = "https://graph.mapillary.com/images"
ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
IMAGE_FIELDS = "id,computed_geometry,thumb_original_url,captured_at"  # The fields of each image record retrieved, defined here: https://www.mapillary.com/developer/api-documentation#image
LOG_DIR = Path("log")
LOG_DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"

DETECTIONS = ['animal--bird', 'animal--ground-animal', 'construction--barrier--acoustic', 'construction--barrier--ambiguous', 'construction--barrier--concrete-block', 'construction--barrier--curb', 'construction--barrier--fence', 'construction--barrier--guard-rail', 'construction--barrier--other-barrier', 'construction--barrier--road-median', 'construction--barrier--road-side', 'construction--barrier--separator', 'construction--barrier--temporary', 'construction--barrier--wall', 'construction--flat--bike-lane', 'construction--flat--crosswalk-plain', 'construction--flat--curb-cut', 'construction--flat--driveway', 'construction--flat--parking', 'construction--flat--parking-aisle', 'construction--flat--pedestrian-area', 'construction--flat--rail-track', 'construction--flat--road-shoulder', 'construction--flat--service-lane', 'construction--flat--sidewalk', 'construction--flat--traffic-island', 'construction--structure--bridge', 'construction--structure--garage', 'construction--structure--tunnel', 'marking--continuous--dashed', 'marking--continuous--solid', 'marking--continuous--zigzag', 'marking--discrete--ambiguous', 'marking--discrete--arrow--ambiguous', 'marking--discrete--arrow--left', 'marking--discrete--arrow--other', 'marking--discrete--arrow--right', 'marking--discrete--arrow--split-left-or-right', 'marking--discrete--arrow--split-left-or-right-or-straight', 'marking--discrete--arrow--split-left-or-straight', 'marking--discrete--arrow--split-right-or-straight', 'marking--discrete--arrow--straight', 'marking--discrete--arrow--u-turn', 'marking--discrete--crosswalk-zebra', 'marking--discrete--give-way-row', 'marking--discrete--give-way-single', 'marking--discrete--hatched--chevron', 'marking--discrete--hatched--diagonal', 'marking--discrete--other-marking', 'marking--discrete--stop-line', 'marking--discrete--symbol--ambiguous', 'marking--discrete--symbol--bicycle', 'marking--discrete--symbol--other', 'marking--discrete--symbol--pedestrian', 'marking--discrete--symbol--wheelchair', 'marking--discrete--text--30', 'marking--discrete--text--40', 'marking--discrete--text--50', 'marking--discrete--text--ambiguous', 'marking--discrete--text--bus', 'marking--discrete--text--other', 'marking--discrete--text--school', 'marking--discrete--text--slow', 'marking--discrete--text--stop', 'marking--discrete--text--taxi', 'object--banner', 'object--bench', 'object--bike-rack', 'object--catch-basin', 'object--cctv-camera', 'object--fire-hydrant', 'object--junction-box', 'object--mailbox', 'object--manhole', 'object--parking-meter', 'object--phone-booth', 'object--pothole', 'object--ramp', 'object--sign--advertisement', 'object--sign--ambiguous', 'object--sign--back', 'object--sign--information', 'object--sign--other', 'object--sign--store', 'object--street-light', 'object--support--pole', 'object--support--pole-group', 'object--support--traffic-sign-frame', 'object--support--utility-pole', 'object--traffic-cone', 'object--traffic-light--ambiguous', 'object--traffic-light--cyclists-back', 'object--traffic-light--cyclists-front', 'object--traffic-light--cyclists-side', 'object--traffic-light--general-horizontal-back', 'object--traffic-light--general-horizontal-front', 'object--traffic-light--general-horizontal-side', 'object--traffic-light--general-single-back', 'object--traffic-light--general-single-front', 'object--traffic-light--general-single-side', 'object--traffic-light--general-upright-back', 'object--traffic-light--general-upright-front', 'object--traffic-light--general-upright-side', 'object--traffic-light--other', 'object--traffic-light--pedestrians-back', 'object--traffic-light--pedestrians-front', 'object--traffic-light--pedestrians-side', 'object--traffic-light--warning', 'object--traffic-sign--ambiguous', 'object--traffic-sign--back', 'object--traffic-sign--direction-back', 'object--traffic-sign--direction-front', 'object--traffic-sign--front', 'object--traffic-sign--information-parking', 'object--traffic-sign--temporary-back', 'object--traffic-sign--temporary-front', 'object--trash-can', 'object--vehicle--bicycle', 'object--vehicle--boat', 'object--vehicle--bus', 'object--vehicle--car', 'object--vehicle--caravan', 'object--vehicle--motorcycle', 'object--vehicle--on-rails', 'object--vehicle--other-vehicle', 'object--vehicle--trailer', 'object--vehicle--truck', 'object--vehicle--vehicle-group', 'object--vehicle--wheeled-slow', 'object--water-valve']


class Record:
    """ A record for a single image """

    def __init__(self, json_data: Dict):
        # Check if all necessary attributes exist
        for field in IMAGE_FIELDS.split(','):
            if field not in json_data:
                print(f"[!!] Critical Error: Field {field} does not exist in JSON data. JSON data dump: {json_data}")
                exit(1)

        self.id = json_data["id"]
        self.url = json_data["thumb_original_url"]

        # Format timestamp as a time object
        ts = json_data["captured_at"] / (10 ** 3)  # returned time is in milliseconds
        self.timestamp = gmtime(ts)

        # Parse computed_geometry of data
        geom = json_data["computed_geometry"]
        if not (geom["type"] == "Point"):
            raise ValueError("Non-Point image detected")

        try:
            self.lon, self.lat = [float(coord) for coord in geom["coordinates"]]  # GeoJSON coordinates are in (lon, lat)
        except ValueError:
            raise ValueError(f"Could not parse coordinates. Coordinates: {geom['coordinates']}")


def main(coord_sw: str, coord_ne: str, detections_str: str = None, max_images: int = 100):
    # Compute the coordinates
    try:
        min_lat, min_lon = [float(coord) for coord in coord_sw.split(',')]
        max_lat, max_lon = [float(coord) for coord in coord_ne.split(',')]
        if min_lat > max_lat or min_lon > max_lon:
            print("[!] Invalid bounding box. Ensure you have inputted the SOUTH-WEST and NORTH-EAST coordinates.")
            exit(1)
    except ValueError:
        print("[!] Invalid coordinates given, please check your coordinates.")
        exit(1)

    bbox = [min_lon, min_lat, max_lon, max_lat]
    records = None

    if detections_str is not None:
        detections = []
        for detection in detections_str.split(','):
            detection = detection.strip()
            if detection not in DETECTIONS:
                print(f"[!] Invalid detection feature \"{detection}\"")
                exit(1)
            detections.append(detection)
        records = search_images(bbox, limit=max_images, detections=detections)
    else:
        records = search_images(bbox, limit=max_images)

    # Extract image records
    if len(records) == 0:
        print(f"[*] No images found.")
        exit(0)
    if "err_code" in records:
        print(f"[!] Error in extracting image records. Error code {records['err_code']} with request URL {records['req_url']}.")
        exit(1)
    print(f"[*] Saving to log file...")

    # Save records to file
    log_filename = store_records(records, bbox)

    print(f"[*] Saved {len(records)} images to: {log_filename}")


def search_images(bbox: List[float], limit: int = 100, captured_before: int = None, captured_after: int = None, detections: List[str] = None) -> Any:
    """
    Returns records for images in the bounding box and within the timestamp range.
    - `bbox`: Defines the bounding box to search for images: [min_lon, min_lat, max_lon, max_lat]
    - `limit`: Maximum number of images. Default is 100, maximum is 2000 according to API.
    - `captured_before`, `captured_after`: The Unix timestamp in NANOSECONDS.
        - `captured_before`: Extract images captured before this timestamp.
        - `captured_after`: Extract images captured after this timestamp.
    """
    # Check parameters
    if bbox[0] > bbox[2]:
        raise ValueError(f"search_images: min_lon ({bbox[0]}) > max_lon ({bbox[2]})")
    if bbox[1] > bbox[3]:
        raise ValueError(f"search_images: min_lat ({bbox[1]}) > max_lat ({bbox[3]})")
    if captured_before is not None and captured_after is not None:
        if captured_after > captured_before:
            raise ValueError(f"search_images: captured_after ({captured_after}) > captured_before ({captured_before})")
    if limit < 0 or limit > 2000:
        raise ValueError(f"search_images: limit should be in range [0, 2000].")

    # Generate query params
    fields = IMAGE_FIELDS
    if detections is not None:
        fields += ",detections.value"
    params = f"access_token={API_KEY}&fields={fields}"
    params += f"&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    if captured_before is not None:
        timestruct = gmtime(captured_before / (10 ** 9))
        iso8601_time = strftime(ISO8601_FORMAT, timestruct)
        params += f"&end_captured_at={iso8601_time}"
    if captured_after is not None:
        timestruct = gmtime(captured_after / (10 ** 9))
        iso8601_time = strftime(ISO8601_FORMAT, timestruct)
        params += f"&start_captured_at={iso8601_time}"
    params += f"&limit={limit}"
    api_url = f"{API_URL}?{params}"

    # Send the request
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()["data"]
        if len(data) == 0:
            return []

        # Parse through data
        records = []
        for datum in data:
            if detections is not None:
                # Only add if the image contains what we are looking for
                try:
                    img_detections = datum["detections"]["data"]
                    for img_detection in img_detections:
                        value = img_detection["value"]
                        if value in detections:
                            # It's inside, add it as a record
                            records.append(Record(datum))
                            continue
                except KeyError:
                    continue
            else:
                records.append(Record(datum))

        return records
    return {
        "err_code": response.status_code,
        "req_url": api_url,
    }


def store_records(records: List[Record], bbox: List[float]) -> str:
    # Ensure log directory exists
    try:
        LOG_DIR.mkdir(exist_ok=True)
    except FileExistsError:
        print(f"[!] Could not create directory {LOG_DIR}. Check if it already exists as a file, and if you have write permissions to it.")
        exit(1)

    # Generate file name (Log_YYYY-MM-DD_hh-mm-ss.html)
    log_file = LOG_DIR.joinpath(f"Log_{strftime(LOG_DATE_FORMAT, gmtime())}.html")
    with log_file.open(mode='w', encoding="utf-8") as fp:
        fp.write("<html>\r\n\t<head></head>\r\n\t<body>\r\n")

        # Write the photo links to the HTML file.
        for record in records:
            osm_link = f"https://www.openstreetmap.org/?mlat={record.lat}&mlon={record.lon}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            fp.write(f"\t\t<a href='{osm_link}' target='_blank'>")
            fp.write(f"<img src='{record.url}' border='0' />")
            fp.write(f"</a><br />\r\n")

        fp.write("\t</body>\r\n</html>")

    return str(log_file.resolve())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Extracts images within a given bounding box and date range."
    )
    parser.add_argument("southwest", type=str, help="South-West Coordinates of the Bounding Box, as latitude, longitude. Example: \"1.3518580962691118,103.93356798061131\"")
    parser.add_argument("northeast", type=str, help="North-East Coordinates of the Bounding Box, as latitude, longitude. Example: \"1.3552656368803468,103.93720991127293\"")
    parser.add_argument("-l", "--limit", type=int, help="Maximum number of images", default=None)
    parser.add_argument("-d", "--detections", type=str, help="Detections to search for (see https://www.mapillary.com/developer/api-documentation/detections).", default=None)
    args = parser.parse_args()

    main(args.southwest, args.northeast, max_images=args.limit, detections_str=args.detections)

# SPDX-License-Identifier: PROPRIETARY
"""Region definitions for behavioral forecasting."""
from dataclasses import dataclass
from typing import Literal, Optional

# Region type definitions
RegionType = Literal["city", "state", "country"]
RegionGroup = Literal[
    "GLOBAL_CITIES", "US_STATES", "EUROPE", "ASIA_PACIFIC", "LATAM", "AFRICA"
]


@dataclass
class Region:
    """Represents a geographic region for forecasting."""

    id: str
    name: str
    country: str
    region_type: RegionType
    latitude: float
    longitude: float
    region_group: Optional[RegionGroup] = None

    def __post_init__(self) -> None:
        """Validate region data."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(
                f"Latitude must be between -90 and 90, got {self.latitude}"
            )
        if not (-180 <= self.longitude <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got {self.longitude}"
            )
        # Auto-assign region_group if not provided
        if self.region_group is None:
            if self.region_type == "city" and self.country == "US":
                self.region_group = "GLOBAL_CITIES"
            elif self.region_type == "city":
                self.region_group = "GLOBAL_CITIES"
            elif self.region_type == "state" and self.country == "US":
                self.region_group = "US_STATES"


# Global cities (existing presets)
GLOBAL_CITIES = [
    Region(
        id="city_nyc",
        name="New York City",
        country="US",
        region_type="city",
        latitude=40.7128,
        longitude=-74.0060,
        region_group="GLOBAL_CITIES",
    ),
    Region(
        id="city_london",
        name="London",
        country="GB",
        region_type="city",
        latitude=51.5074,
        longitude=-0.1278,
        region_group="GLOBAL_CITIES",
    ),
    Region(
        id="city_tokyo",
        name="Tokyo",
        country="JP",
        region_type="city",
        latitude=35.6762,
        longitude=139.6503,
        region_group="GLOBAL_CITIES",
    ),
]

# Additional global cities for expanded coverage
ADDITIONAL_GLOBAL_CITIES = [
    # North America
    Region(
        id="city_la",
        name="Los Angeles",
        country="US",
        region_type="city",
        latitude=34.0522,
        longitude=-118.2437,
        region_group="GLOBAL_CITIES",
    ),
    # Europe
    Region(
        id="city_paris",
        name="Paris",
        country="FR",
        region_type="city",
        latitude=48.8566,
        longitude=2.3522,
        region_group="EUROPE",
    ),
    Region(
        id="city_berlin",
        name="Berlin",
        country="DE",
        region_type="city",
        latitude=52.5200,
        longitude=13.4050,
        region_group="EUROPE",
    ),
    # Asia-Pacific
    Region(
        id="city_sydney",
        name="Sydney",
        country="AU",
        region_type="city",
        latitude=-33.8688,
        longitude=151.2093,
        region_group="ASIA_PACIFIC",
    ),
    Region(
        id="city_singapore",
        name="Singapore",
        country="SG",
        region_type="city",
        latitude=1.3521,
        longitude=103.8198,
        region_group="ASIA_PACIFIC",
    ),
    Region(
        id="city_mumbai",
        name="Mumbai",
        country="IN",
        region_type="city",
        latitude=19.0760,
        longitude=72.8777,
        region_group="ASIA_PACIFIC",
    ),
    # Latin America
    Region(
        id="city_sao_paulo",
        name="São Paulo",
        country="BR",
        region_type="city",
        latitude=-23.5505,
        longitude=-46.6333,
        region_group="LATAM",
    ),
    # Africa
    Region(
        id="city_johannesburg",
        name="Johannesburg",
        country="ZA",
        region_type="city",
        latitude=-26.2041,
        longitude=28.0473,
        region_group="AFRICA",
    ),
]

# US States (50 states + DC) with approximate centroids
US_STATES = [
    Region(
        id="us_al",
        name="Alabama",
        country="US",
        region_type="state",
        latitude=32.806671,
        longitude=-86.791130,
    ),
    Region(
        id="us_ak",
        name="Alaska",
        country="US",
        region_type="state",
        latitude=61.370716,
        longitude=-152.404419,
    ),
    Region(
        id="us_az",
        name="Arizona",
        country="US",
        region_type="state",
        latitude=33.729759,
        longitude=-111.431221,
    ),
    Region(
        id="us_ar",
        name="Arkansas",
        country="US",
        region_type="state",
        latitude=34.969704,
        longitude=-92.373123,
    ),
    Region(
        id="us_ca",
        name="California",
        country="US",
        region_type="state",
        latitude=36.116203,
        longitude=-119.681564,
    ),
    Region(
        id="us_co",
        name="Colorado",
        country="US",
        region_type="state",
        latitude=39.059811,
        longitude=-105.311104,
    ),
    Region(
        id="us_ct",
        name="Connecticut",
        country="US",
        region_type="state",
        latitude=41.597782,
        longitude=-72.755371,
    ),
    Region(
        id="us_de",
        name="Delaware",
        country="US",
        region_type="state",
        latitude=39.318523,
        longitude=-75.507141,
    ),
    Region(
        id="us_dc",
        name="District of Columbia",
        country="US",
        region_type="state",
        latitude=38.907192,
        longitude=-77.036873,
    ),
    Region(
        id="us_fl",
        name="Florida",
        country="US",
        region_type="state",
        latitude=27.766279,
        longitude=-81.686783,
    ),
    Region(
        id="us_ga",
        name="Georgia",
        country="US",
        region_type="state",
        latitude=33.040619,
        longitude=-83.643074,
    ),
    Region(
        id="us_hi",
        name="Hawaii",
        country="US",
        region_type="state",
        latitude=21.094318,
        longitude=-157.498337,
    ),
    Region(
        id="us_id",
        name="Idaho",
        country="US",
        region_type="state",
        latitude=44.240459,
        longitude=-114.478828,
    ),
    Region(
        id="us_il",
        name="Illinois",
        country="US",
        region_type="state",
        latitude=40.349457,
        longitude=-88.986137,
    ),
    Region(
        id="us_in",
        name="Indiana",
        country="US",
        region_type="state",
        latitude=39.849426,
        longitude=-86.258278,
    ),
    Region(
        id="us_ia",
        name="Iowa",
        country="US",
        region_type="state",
        latitude=42.011539,
        longitude=-93.210526,
    ),
    Region(
        id="us_ks",
        name="Kansas",
        country="US",
        region_type="state",
        latitude=38.526600,
        longitude=-96.726486,
    ),
    Region(
        id="us_ky",
        name="Kentucky",
        country="US",
        region_type="state",
        latitude=37.668140,
        longitude=-84.670067,
    ),
    Region(
        id="us_la",
        name="Louisiana",
        country="US",
        region_type="state",
        latitude=31.169546,
        longitude=-91.867805,
    ),
    Region(
        id="us_me",
        name="Maine",
        country="US",
        region_type="state",
        latitude=44.323535,
        longitude=-69.765261,
    ),
    Region(
        id="us_md",
        name="Maryland",
        country="US",
        region_type="state",
        latitude=39.063946,
        longitude=-76.802101,
    ),
    Region(
        id="us_ma",
        name="Massachusetts",
        country="US",
        region_type="state",
        latitude=42.230171,
        longitude=-71.530106,
    ),
    Region(
        id="us_mi",
        name="Michigan",
        country="US",
        region_type="state",
        latitude=43.326618,
        longitude=-84.536095,
    ),
    Region(
        id="us_mn",
        name="Minnesota",
        country="US",
        region_type="state",
        latitude=46.729553,
        longitude=-94.685900,
    ),
    Region(
        id="us_ms",
        name="Mississippi",
        country="US",
        region_type="state",
        latitude=32.741646,
        longitude=-89.678696,
    ),
    Region(
        id="us_mo",
        name="Missouri",
        country="US",
        region_type="state",
        latitude=38.456085,
        longitude=-92.288368,
    ),
    Region(
        id="us_mt",
        name="Montana",
        country="US",
        region_type="state",
        latitude=46.921925,
        longitude=-110.454353,
    ),
    Region(
        id="us_ne",
        name="Nebraska",
        country="US",
        region_type="state",
        latitude=41.125370,
        longitude=-98.268082,
    ),
    Region(
        id="us_nv",
        name="Nevada",
        country="US",
        region_type="state",
        latitude=38.313515,
        longitude=-117.055374,
    ),
    Region(
        id="us_nh",
        name="New Hampshire",
        country="US",
        region_type="state",
        latitude=43.452492,
        longitude=-71.563896,
    ),
    Region(
        id="us_nj",
        name="New Jersey",
        country="US",
        region_type="state",
        latitude=40.298904,
        longitude=-74.521011,
    ),
    Region(
        id="us_nm",
        name="New Mexico",
        country="US",
        region_type="state",
        latitude=34.840515,
        longitude=-106.248482,
    ),
    Region(
        id="us_ny",
        name="New York",
        country="US",
        region_type="state",
        latitude=42.165726,
        longitude=-74.948051,
    ),
    Region(
        id="us_nc",
        name="North Carolina",
        country="US",
        region_type="state",
        latitude=35.630066,
        longitude=-79.806419,
    ),
    Region(
        id="us_nd",
        name="North Dakota",
        country="US",
        region_type="state",
        latitude=47.528912,
        longitude=-99.784012,
    ),
    Region(
        id="us_oh",
        name="Ohio",
        country="US",
        region_type="state",
        latitude=40.388783,
        longitude=-82.764915,
    ),
    Region(
        id="us_ok",
        name="Oklahoma",
        country="US",
        region_type="state",
        latitude=35.565342,
        longitude=-96.928917,
    ),
    Region(
        id="us_or",
        name="Oregon",
        country="US",
        region_type="state",
        latitude=44.572021,
        longitude=-122.070938,
    ),
    Region(
        id="us_pa",
        name="Pennsylvania",
        country="US",
        region_type="state",
        latitude=40.590752,
        longitude=-77.209755,
    ),
    Region(
        id="us_ri",
        name="Rhode Island",
        country="US",
        region_type="state",
        latitude=41.680893,
        longitude=-71.51178,
    ),
    Region(
        id="us_sc",
        name="South Carolina",
        country="US",
        region_type="state",
        latitude=33.856892,
        longitude=-80.945007,
    ),
    Region(
        id="us_sd",
        name="South Dakota",
        country="US",
        region_type="state",
        latitude=44.299782,
        longitude=-99.438828,
    ),
    Region(
        id="us_tn",
        name="Tennessee",
        country="US",
        region_type="state",
        latitude=35.747845,
        longitude=-86.692345,
    ),
    Region(
        id="us_tx",
        name="Texas",
        country="US",
        region_type="state",
        latitude=31.054487,
        longitude=-97.563461,
    ),
    Region(
        id="us_ut",
        name="Utah",
        country="US",
        region_type="state",
        latitude=40.150032,
        longitude=-111.862434,
    ),
    Region(
        id="us_vt",
        name="Vermont",
        country="US",
        region_type="state",
        latitude=44.045876,
        longitude=-72.710686,
    ),
    Region(
        id="us_va",
        name="Virginia",
        country="US",
        region_type="state",
        latitude=37.769337,
        longitude=-78.169968,
    ),
    Region(
        id="us_wa",
        name="Washington",
        country="US",
        region_type="state",
        latitude=47.400902,
        longitude=-121.490494,
    ),
    Region(
        id="us_wv",
        name="West Virginia",
        country="US",
        region_type="state",
        latitude=38.491226,
        longitude=-80.954453,
    ),
    Region(
        id="us_wi",
        name="Wisconsin",
        country="US",
        region_type="state",
        latitude=44.268543,
        longitude=-89.616508,
    ),
    Region(
        id="us_wy",
        name="Wyoming",
        country="US",
        region_type="state",
        latitude=42.755966,
        longitude=-107.302490,
    ),
]

# Assign region_group to all US states
for state in US_STATES:
    if state.region_group is None:
        state.region_group = "US_STATES"


def get_all_regions() -> list[Region]:
    """
    Get all available regions (global cities + US states + additional global regions).

    Returns:
        List of all Region objects, sorted by region_group, then region_type, then name.
    """
    all_regions = GLOBAL_CITIES + ADDITIONAL_GLOBAL_CITIES + US_STATES
    return sorted(
        all_regions,
        key=lambda r: (
            r.region_group or "ZZZ",  # Put ungrouped regions last
            r.region_type,
            r.name,
        ),
    )


def get_region_by_id(region_id: str) -> Region | None:
    """
    Look up a region by its ID.

    Args:
        region_id: The region identifier (e.g., "us_mn", "city_nyc")

    Returns:
        Region object if found, None otherwise.
    """
    all_regions = get_all_regions()
    for region in all_regions:
        if region.id == region_id:
            return region
    return None

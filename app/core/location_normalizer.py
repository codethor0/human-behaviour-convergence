# SPDX-License-Identifier: PROPRIETARY
"""Location normalization for behavioral forecasting.

Maps natural language location descriptions to canonical region_id values,
handling edge cases like Washington D.C. vs Washington state, incident location
vs home state, and city vs state disambiguation.
"""
from dataclasses import dataclass
from typing import List, Optional

from app.core.regions import Region, get_all_regions, get_region_by_id


@dataclass
class NormalizedLocation:
    """Result of location normalization."""

    region_id: str
    region_label: str
    reason: str
    alternatives: List[str]
    notes: List[str]


@dataclass
class LocationNormalizationResult:
    """Complete normalization result with metadata."""

    task: str = "normalize_location_for_forecast"
    input_description: str = ""
    normalized_location: Optional[NormalizedLocation] = None
    best_guess_region_id: Optional[str] = None
    alternate_region_ids: List[str] = None
    ambiguity_reason: Optional[str] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.alternate_region_ids is None:
            self.alternate_region_ids = []


class LocationNormalizer:
    """Normalizes natural language location descriptions to region_id."""

    # Federal building/landmark keywords that indicate Washington D.C.
    DC_KEYWORDS = [
        "white house",
        "capitol",
        "congress",
        "senate",
        "house of representatives",
        "supreme court",
        "national mall",
        "washington monument",
        "lincoln memorial",
        "pentagon",
        "fbi headquarters",
        "federal",
        "us capital",
        "national capital",
    ]

    # City-like context keywords
    CITY_KEYWORDS = [
        "subway",
        "metro",
        "borough",
        "manhattan",
        "brooklyn",
        "queens",
        "bronx",
        "times square",
        "wall street",
        "downtown",
        "uptown",
        "midtown",
        "urban",
    ]

    # State-wide/rural context keywords
    STATE_KEYWORDS = [
        "upstate",
        "rural",
        "state-wide",
        "statewide",
        "across the state",
        "entire state",
        "state of",
    ]

    # Washington state indicators
    WA_STATE_KEYWORDS = [
        "seattle",
        "spokane",
        "tacoma",
        "bellevue",
        "everett",
        "pacific northwest",
        "pnw",
        "cascades",
        "mount rainier",
    ]

    def __init__(self):
        """Initialize the normalizer with region registry."""
        self.regions = get_all_regions()
        self._build_lookup_maps()

    def _build_lookup_maps(self):
        """Build lookup maps for efficient region matching."""
        # Map lowercase names to regions
        self.name_map = {}
        self.alias_map = {}

        for region in self.regions:
            # Primary name mapping
            key = region.name.lower()
            if key not in self.name_map:
                self.name_map[key] = []
            self.name_map[key].append(region)

            # Alias mappings
            aliases = self._generate_aliases(region)
            for alias in aliases:
                alias_lower = alias.lower()
                if alias_lower not in self.alias_map:
                    self.alias_map[alias_lower] = []
                self.alias_map[alias_lower].append(region)

    def _generate_aliases(self, region: Region) -> List[str]:
        """Generate common aliases for a region."""
        aliases = []
        name_lower = region.name.lower()

        # Common abbreviations
        if region.region_type == "state" and region.country == "US":
            # State abbreviations (e.g., "CA" for California)
            state_abbrevs = {
                "alabama": "al",
                "alaska": "ak",
                "arizona": "az",
                "arkansas": "ar",
                "california": "ca",
                "colorado": "co",
                "connecticut": "ct",
                "delaware": "de",
                "district of columbia": "dc",
                "florida": "fl",
                "georgia": "ga",
                "hawaii": "hi",
                "idaho": "id",
                "illinois": "il",
                "indiana": "in",
                "iowa": "ia",
                "kansas": "ks",
                "kentucky": "ky",
                "louisiana": "la",
                "maine": "me",
                "maryland": "md",
                "massachusetts": "ma",
                "michigan": "mi",
                "minnesota": "mn",
                "mississippi": "ms",
                "missouri": "mo",
                "montana": "mt",
                "nebraska": "ne",
                "nevada": "nv",
                "new hampshire": "nh",
                "new jersey": "nj",
                "new mexico": "nm",
                "new york": "ny",
                "north carolina": "nc",
                "north dakota": "nd",
                "ohio": "oh",
                "oklahoma": "ok",
                "oregon": "or",
                "pennsylvania": "pa",
                "rhode island": "ri",
                "south carolina": "sc",
                "south dakota": "sd",
                "tennessee": "tn",
                "texas": "tx",
                "utah": "ut",
                "vermont": "vt",
                "virginia": "va",
                "washington": "wa",
                "west virginia": "wv",
                "wisconsin": "wi",
                "wyoming": "wy",
            }
            if name_lower in state_abbrevs:
                abbrev = state_abbrevs[name_lower]
                aliases.append(f"us_{abbrev}")
                # Also add standalone abbreviation for matching
                aliases.append(abbrev)

        # City aliases
        if region.id == "city_nyc":
            aliases.extend(
                [
                    "nyc",
                    "new york city",
                    "manhattan",
                    "brooklyn",
                    "times square",
                    "wall street",
                ]
            )
        elif region.id == "city_la":
            aliases.extend(["los angeles", "la", "l.a."])
        elif region.id == "city_london":
            aliases.extend(["london"])
        elif region.id == "city_tokyo":
            aliases.extend(["tokyo"])
        elif region.id == "city_sao_paulo":
            aliases.extend(["sao paulo", "são paulo"])
        elif region.id == "city_johannesburg":
            aliases.extend(["johannesburg"])

        # Washington D.C. aliases
        if region.id == "us_dc":
            aliases.extend(
                [
                    "washington d.c.",
                    "washington dc",
                    "washington, d.c.",
                    "washington, dc",
                    "dc",
                    "district of columbia",
                    "d.c.",
                ]
            )

        return aliases

    def normalize(
        self, description: str, explicit_location: Optional[str] = None
    ) -> LocationNormalizationResult:
        """
        Normalize a location description to a region_id.

        Args:
            description: Natural language description of an event/incident
            explicit_location: Optional explicit location (city, state, country)

        Returns:
            LocationNormalizationResult with normalized location and metadata
        """
        result = LocationNormalizationResult(input_description=description)

        # Combine description and explicit location for analysis
        text = f"{description} {explicit_location or ''}".lower()

        # Rule 1: Check for incident location vs home state
        # Look for patterns like "X from Y" or "X in Y" where Y is the incident location
        incident_location = self._extract_incident_location(text, description)

        # Rule 2: Washington D.C. vs Washington state disambiguation
        if self._is_washington_dc(text):
            region = get_region_by_id("us_dc")
            if region:
                result.normalized_location = NormalizedLocation(
                    region_id=region.id,
                    region_label=region.name,
                    reason=(
                        "Description contains federal building/landmark keywords "
                        "or explicitly mentions Washington, D.C."
                    ),
                    alternatives=[],
                    notes=[
                        "Washington D.C. (us_dc) is distinct from Washington state (us_wa).",
                        "Federal buildings, White House, Capitol indicate D.C.",
                    ],
                )
                return result

        # Rule 3: City vs state disambiguation
        # First check for "City, State" patterns and handle them specially
        import re

        city_state_pattern = r"([A-Z][a-z]+),\s*([A-Z][a-z]+)"
        city_state_match = re.search(city_state_pattern, description)
        if city_state_match:
            city_name = city_state_match.group(1).lower()
            state_name = city_state_match.group(2).lower()

            # Check if city is a known city in our registry
            city_region = self._match_location(city_name)
            if city_region and city_region.region_type == "city":
                result.normalized_location = NormalizedLocation(
                    region_id=city_region.id,
                    region_label=city_region.name,
                    reason=f"Matched city from 'City, State' pattern: {city_name}",
                    alternatives=[],
                    notes=[],
                )
                return result

            # If city not found but state is Washington, check for Washington state cities
            if state_name == "washington":
                if city_name in self.WA_STATE_KEYWORDS:
                    region = get_region_by_id("us_wa")
                    if region:
                        result.normalized_location = NormalizedLocation(
                            region_id=region.id,
                            region_label=region.name,
                            reason=(
                                f"Matched Washington state from city context: "
                                f"{city_name}, Washington"
                            ),
                            alternatives=["us_dc"],
                            notes=[],
                        )
                        return result

        # Regular city matching
        city_region = self._try_city_match(text, description)
        if city_region:
            result.normalized_location = NormalizedLocation(
                region_id=city_region.id,
                region_label=city_region.name,
                reason=f"Matched to city-level region: {city_region.name}",
                alternatives=[],
                notes=[],
            )
            return result

        # Rule 4: Try explicit location match
        if explicit_location:
            explicit_region = self._match_location(explicit_location)
            if explicit_region:
                result.normalized_location = NormalizedLocation(
                    region_id=explicit_region.id,
                    region_label=explicit_region.name,
                    reason=f"Matched explicit location: {explicit_location}",
                    alternatives=[],
                    notes=[],
                )
                return result

        # Rule 5: Try state match
        state_region = self._try_state_match(text, description)
        if state_region:
            result.normalized_location = NormalizedLocation(
                region_id=state_region.id,
                region_label=state_region.name,
                reason=f"Matched to state-level region: {state_region.name}",
                alternatives=[],
                notes=[],
            )
            return result

        # Rule 6: Try incident location if extracted (but check for ambiguity first)
        if incident_location:
            # Special handling for ambiguous "Washington"
            if incident_location.lower() == "washington":
                # Check if it's clearly D.C. or state
                if self._is_washington_dc(text):
                    region = get_region_by_id("us_dc")
                    if region:
                        result.normalized_location = NormalizedLocation(
                            region_id=region.id,
                            region_label=region.name,
                            reason="Extracted incident location: Washington (D.C. context)",
                            alternatives=["us_wa"],
                            notes=[
                                "Washington could refer to state or D.C.; D.C. context detected."
                            ],
                        )
                        return result
                # Check for state context (check original description, not just extracted)
                elif any(kw in description.lower() for kw in self.WA_STATE_KEYWORDS):
                    region = get_region_by_id("us_wa")
                    if region:
                        result.normalized_location = NormalizedLocation(
                            region_id=region.id,
                            region_label=region.name,
                            reason=(
                                "Extracted incident location: Washington "
                                "(state context from description)"
                            ),
                            alternatives=["us_dc"],
                            notes=[
                                "Washington could refer to state or D.C.; "
                                "state context detected (e.g., Seattle)."
                            ],
                        )
                        return result
                # Truly ambiguous - handle in ambiguity section
            else:
                # For non-Washington locations, match normally but prefer exact matches
                region = self._match_location(incident_location)
                if region:
                    # Double-check: if we extracted from a comma-separated location like "Seattle, Washington",
                    # make sure we're using the right part
                    if "," in description and incident_location.lower() == "washington":
                        # Check if there's a city before the comma that suggests Washington state
                        import re

                        city_state_pattern = r"([A-Z][a-z]+),\s*Washington"
                        match = re.search(city_state_pattern, description)
                        if match:
                            city = match.group(1).lower()
                            if city in self.WA_STATE_KEYWORDS:
                                region = get_region_by_id("us_wa")
                                if region:
                                    result.normalized_location = NormalizedLocation(
                                        region_id=region.id,
                                        region_label=region.name,
                                        reason=(
                                            f"Extracted incident location: "
                                            f"Washington (state, from '{city}, "
                                            f"Washington')"
                                        ),
                                        alternatives=["us_dc"],
                                        notes=[],
                                    )
                                    return result

                    result.normalized_location = NormalizedLocation(
                        region_id=region.id,
                        region_label=region.name,
                        reason=f"Extracted incident location: {incident_location}",
                        alternatives=[],
                        notes=[],
                    )
                    return result

        # Rule 7: Ambiguity handling - return best guess with alternatives
        best_guess, alternatives, reason = self._handle_ambiguity(text, description)
        result.best_guess_region_id = best_guess
        result.alternate_region_ids = alternatives
        result.ambiguity_reason = reason

        return result

    def _is_washington_dc(self, text: str) -> bool:
        """Check if text refers to Washington D.C. (not Washington state)."""
        # Check for explicit D.C. mentions
        dc_patterns = [
            "washington d.c.",
            "washington dc",
            "washington, d.c.",
            "washington, dc",
            "district of columbia",
            "d.c.",
        ]
        for pattern in dc_patterns:
            if pattern in text:
                return True

        # Check for federal building keywords
        for keyword in self.DC_KEYWORDS:
            if keyword in text:
                return True

        # Check for Washington without state indicators
        if "washington" in text:
            # If it has Washington state keywords, it's NOT D.C.
            for wa_keyword in self.WA_STATE_KEYWORDS:
                if wa_keyword in text:
                    return False
            # If no state keywords, check if it has D.C. context
            if any(dc_kw in text for dc_kw in self.DC_KEYWORDS):
                return True
            # Ambiguous - default to D.C. if federal context, otherwise ambiguous
            # This will be handled in _handle_ambiguity

        return False

    def _try_city_match(self, text: str, description: str) -> Optional[Region]:
        """Try to match to a city-level region."""
        # Check for city keywords in description
        has_city_context = any(kw in description.lower() for kw in self.CITY_KEYWORDS)
        has_state_context = any(kw in description.lower() for kw in self.STATE_KEYWORDS)

        # If state context is present, prefer state over city
        if has_state_context and not has_city_context:
            return None

        # Try to match city names and aliases
        for region in self.regions:
            if region.region_type == "city":
                # Check name
                if region.name.lower() in text:
                    return region
                # Check aliases (including landmarks)
                aliases = self._generate_aliases(region)
                for alias in aliases:
                    if alias.lower() in text:
                        return region

        return None

    def _try_state_match(self, text: str, description: str) -> Optional[Region]:
        """Try to match to a state-level region."""
        # Check for state keywords
        has_state_context = any(kw in description.lower() for kw in self.STATE_KEYWORDS)

        import re

        # First, try state abbreviations (2-letter codes like "NY", "CA")
        # Extract potential abbreviations from text
        abbrev_pattern = r"\b([A-Z]{2})\b"
        abbrev_matches = re.findall(abbrev_pattern, description)
        for abbrev in abbrev_matches:
            abbrev_lower = abbrev.lower()
            abbrev_region_id = f"us_{abbrev_lower}"
            region = get_region_by_id(abbrev_region_id)
            if region:
                # Special handling for Washington
                if region.id == "us_wa":
                    if has_state_context or any(
                        kw in text for kw in self.WA_STATE_KEYWORDS
                    ):
                        return region
                    continue
                return region

        # Then try to match state names (use word boundaries for better matching)
        # Sort by name length (longer first) to avoid partial matches
        state_regions = [r for r in self.regions if r.region_type == "state"]
        state_regions.sort(key=lambda r: len(r.name), reverse=True)

        for region in state_regions:
            # Check name with word boundaries - must be a complete word
            pattern = r"\b" + re.escape(region.name.lower()) + r"\b"
            if re.search(pattern, text):
                # Special handling for Washington
                if region.id == "us_wa":
                    # Only match if it's clearly the state (has state keywords or no D.C. context)
                    if has_state_context or any(
                        kw in text for kw in self.WA_STATE_KEYWORDS
                    ):
                        return region
                    # If ambiguous, don't match here (will be handled in ambiguity)
                    continue
                return region
            # Check aliases with word boundaries
            aliases = self._generate_aliases(region)
            for alias in aliases:
                # Skip single-letter or very short aliases that might cause false matches
                if len(alias) <= 2:
                    continue
                alias_pattern = r"\b" + re.escape(alias.lower()) + r"\b"
                if re.search(alias_pattern, text):
                    if region.id == "us_wa":
                        # Same special handling
                        if has_state_context or any(
                            kw in text for kw in self.WA_STATE_KEYWORDS
                        ):
                            return region
                        continue
                    return region

        return None

    def _extract_incident_location(self, text: str, description: str) -> Optional[str]:
        """
        Extract incident location from description.

        Looks for patterns like:
        - "X from Y in Z" -> Z is incident location
        - "X in Y" -> Y is incident location
        - "near X" -> X is incident location
        """
        # Look for "in [location]" pattern
        import re

        # Pattern: "in [location]" or "near [location]" - improved to handle commas and multi-word locations
        patterns = [
            r"in\s+([A-Z][a-zA-Z\s,]+?)(?:\s|,|\.|$)",  # "in Washington, D.C."
            # or "in Seattle, Washington"
            r"near\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:\s|,|\.|$)",  # "near the White House"
            # or "near Washington"
            r"at\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:\s|,|\.|$)",  # "at the Capitol"
            # or "at Washington"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description)
            if matches:
                # Clean up the match and return the last one (most specific location)
                location = matches[-1].strip().rstrip(".,")
                # If it contains a comma, take the part after the comma (e.g., "Seattle, Washington" -> "Washington")
                if "," in location:
                    parts = [p.strip() for p in location.split(",")]
                    # Prefer the state/city name over the city if both present
                    if len(parts) > 1:
                        return parts[-1]  # Usually the state
                return location

        return None

    def _match_location(self, location: str) -> Optional[Region]:
        """Match a location string to a region."""
        location_lower = location.lower().strip()

        # Try exact name match
        if location_lower in self.name_map:
            candidates = self.name_map[location_lower]
            # Prefer city over state if both exist
            cities = [r for r in candidates if r.region_type == "city"]
            if cities:
                return cities[0]
            return candidates[0]

        # Try alias match
        if location_lower in self.alias_map:
            candidates = self.alias_map[location_lower]
            cities = [r for r in candidates if r.region_type == "city"]
            if cities:
                return cities[0]
            return candidates[0]

        # Try state abbreviation match (e.g., "NY" -> "us_ny")
        if len(location_lower) == 2 and location_lower.isalpha():
            # Try to find state by abbreviation
            abbrev_region_id = f"us_{location_lower}"
            region = get_region_by_id(abbrev_region_id)
            if region:
                return region

        # Try word-boundary partial match (more strict)
        import re

        for region in self.regions:
            # Use word boundaries to avoid false matches
            # Only check if location is a complete word in region name
            pattern = r"\b" + re.escape(location_lower) + r"\b"
            if re.search(pattern, region.name.lower()):
                return region
            # Also try reverse (region name as complete word in location)
            # But only if location is longer (to avoid "in" matching "Indiana" in "Washington")
            if len(location_lower) >= len(region.name.lower()):
                region_pattern = r"\b" + re.escape(region.name.lower()) + r"\b"
                if re.search(region_pattern, location_lower):
                    return region

        return None

    def _handle_ambiguity(
        self, text: str, description: str
    ) -> tuple[Optional[str], List[str], str]:
        """
        Handle ambiguous location descriptions.

        Returns:
            (best_guess_region_id, alternate_region_ids, reason)
        """
        # Check for Washington ambiguity
        if "washington" in text.lower():
            # Check if it has D.C. indicators
            has_dc_indicators = any(kw in text for kw in self.DC_KEYWORDS)
            has_wa_indicators = any(kw in text for kw in self.WA_STATE_KEYWORDS)

            if has_dc_indicators and not has_wa_indicators:
                return ("us_dc", ["us_wa"], "Washington with D.C. context")
            elif has_wa_indicators and not has_dc_indicators:
                return ("us_wa", ["us_dc"], "Washington with state context")
            else:
                # Truly ambiguous
                return (
                    "us_wa",
                    ["us_dc"],
                    "Washington is ambiguous between state and D.C.; no further context provided.",
                )

        # Default: return None with empty alternatives
        return (None, [], "Could not determine location from description.")


def normalize_location(
    description: str, explicit_location: Optional[str] = None
) -> LocationNormalizationResult:
    """
    Convenience function to normalize a location description.

    Args:
        description: Natural language description of an event/incident
        explicit_location: Optional explicit location (city, state, country)

    Returns:
        LocationNormalizationResult with normalized location and metadata

    Example:
        >>> result = normalize_location(
        ...     "Two West Virginia National Guardsmen were shot near the White House in Washington, D.C."
        ... )
        >>> result.normalized_location.region_id
        'us_dc'
    """
    normalizer = LocationNormalizer()
    return normalizer.normalize(description, explicit_location)

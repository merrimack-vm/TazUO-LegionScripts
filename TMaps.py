import API
import re

# ------------------------------------------------------------
# INFO
# ------------------------------------------------------------

# Scans your backpack for the uncompleted treasure map closest to your location
# Uses a shovel to dig on your location, if you are too far it shows an arrow directing you to the chest location
# Script intended to be used as a hotkey 

# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

SHOVEL = 0x0F39
TREASURE_MAP = 0x14EC

# Show the tracking arrow when farther away than this many tiles.
ARROW_DISTANCE = 15

# Unique ID for our tracking arrow.
ARROW_ID = 987654


# ------------------------------------------------------------
# FACET INFORMATION
# ------------------------------------------------------------

FACETS = {
    0: "Felucca",
    1: "Trammel",
    2: "Ilshenar",
    3: "Malas",
    4: "Tokuno",
    5: "TerMur",
}


# ------------------------------------------------------------
# FIND ITEMS DIRECTLY IN MAIN BACKPACK
# ------------------------------------------------------------

def find_direct_items(graphic):

    # False = don't search inside bags.
    items = API.ItemsInContainer(API.Backpack, False)

    found = []

    for item in items:
        if item.Graphic == graphic:
            found.append(item)

    return found


# ------------------------------------------------------------
# GET TREASURE MAP INFORMATION
# ------------------------------------------------------------

def get_map_info(item):

    props = API.ItemNameAndProps(item.Serial, True, 3)

    if not props:
        return None

    # Example:
    #
    # Chest Location: (1190, 3543)
    #

    location_match = re.search(
        r"Chest\s+Location\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)",
        props,
        re.IGNORECASE
    )

    if not location_match:
        return None

    x = int(location_match.group(1))
    y = int(location_match.group(2))

    # Example:
    #
    # For Somewhere in Trammel
    #

    facet = None

    for facet_name in FACETS.values():

        if re.search(
            r"For\s+Somewhere\s+in\s+" +
            re.escape(facet_name),
            props,
            re.IGNORECASE
        ):
            facet = facet_name
            break

    if facet is None:
        return None

    return facet, x, y, props


# ------------------------------------------------------------
# CHECK WHETHER MAP WAS COMPLETED BY THIS CHARACTER
# ------------------------------------------------------------

def completed_by_player(props):

    player_name = API.Player.Name

    if not player_name:
        return False

    pattern = (
        r"Completed\s+By\s+" +
        re.escape(player_name) +
        r"\b"
    )

    return re.search(
        pattern,
        props,
        re.IGNORECASE
    ) is not None


# ------------------------------------------------------------
# UO TILE DISTANCE
# ------------------------------------------------------------

def tile_distance(x1, y1, x2, y2):

    return max(
        abs(x1 - x2),
        abs(y1 - y2)
    )


# ------------------------------------------------------------
# FIND CLOSEST VALID MAP
# ------------------------------------------------------------

def find_closest_map():

    maps = find_direct_items(TREASURE_MAP)

    if not maps:

        API.SysMsg(
            "No treasure maps found in main backpack!",
            33
        )

        return None

    current_x = API.Player.X
    current_y = API.Player.Y

    current_map_id = API.GetMap()

    current_facet = FACETS.get(
        current_map_id,
        "Unknown"
    )

    API.SysMsg(
        "Current: " +
        str(current_x) + ", " +
        str(current_y) +
        " - " +
        current_facet,
        68
    )

    closest_map = None
    closest_distance = None

    closest_facet = None
    closest_x = None
    closest_y = None

    skipped_completed = 0
    skipped_wrong_facet = 0
    skipped_invalid = 0

    for item in maps:

        if API.StopRequested:
            return None

        info = get_map_info(item)

        if info is None:

            skipped_invalid += 1
            continue

        facet, map_x, map_y, props = info

        # ----------------------------------------------------
        # Ignore maps completed by this character
        # ----------------------------------------------------

        if completed_by_player(props):

            skipped_completed += 1
            continue

        # ----------------------------------------------------
        # Ignore maps on another facet
        # ----------------------------------------------------

        if facet.lower() != current_facet.lower():

            skipped_wrong_facet += 1
            continue

        # ----------------------------------------------------
        # Calculate distance
        # ----------------------------------------------------

        distance = tile_distance(
            current_x,
            current_y,
            map_x,
            map_y
        )

        # ----------------------------------------------------
        # Keep closest map
        # ----------------------------------------------------

        if (
            closest_distance is None
            or distance < closest_distance
        ):

            closest_map = item
            closest_distance = distance

            closest_facet = facet
            closest_x = map_x
            closest_y = map_y

    # --------------------------------------------------------
    # No usable map
    # --------------------------------------------------------

    if closest_map is None:

        API.SysMsg(
            "No usable treasure maps found on " +
            current_facet + "!",
            33
        )

        if skipped_completed > 0:

            API.SysMsg(
                "Ignored " +
                str(skipped_completed) +
                " completed map(s).",
                33
            )

        if skipped_wrong_facet > 0:

            API.SysMsg(
                "Ignored " +
                str(skipped_wrong_facet) +
                " map(s) on other facets.",
                33
            )

        return None

    # --------------------------------------------------------
    # Report selected map
    # --------------------------------------------------------

    API.SysMsg(
        "Nearest treasure map:",
        68
    )

    API.SysMsg(
        closest_facet +
        " (" +
        str(closest_x) +
        ", " +
        str(closest_y) +
        ") - " +
        str(closest_distance) +
        " tiles away",
        68
    )

    # --------------------------------------------------------
    # TRACKING ARROW
    # --------------------------------------------------------

    if closest_distance > ARROW_DISTANCE:

        API.TrackingArrow(
            closest_x,
            closest_y,
            ARROW_ID
        )

        API.SysMsg(
            "Tracking arrow activated.",
            68
        )

    else:

        # Close any previous arrow.
        API.TrackingArrow(
            -1,
            -1,
            ARROW_ID
        )

    return closest_map


# ------------------------------------------------------------
# FIND SHOVEL
# ------------------------------------------------------------

shovels = find_direct_items(SHOVEL)

if not shovels:

    API.SysMsg(
        "No shovel found in main backpack!",
        33
    )

    API.Stop()
    raise SystemExit

shovel = shovels[0]


# ------------------------------------------------------------
# FIND CLOSEST TREASURE MAP
# ------------------------------------------------------------

treasure_map = find_closest_map()

if treasure_map is None:

    API.Stop()
    raise SystemExit


# ------------------------------------------------------------
# USE SHOVEL
# ------------------------------------------------------------

API.SysMsg(
    "Using shovel on nearest treasure map...",
    68
)

API.UseObject(shovel.Serial)


# ------------------------------------------------------------
# WAIT FOR MAP TARGET
# ------------------------------------------------------------

if not API.WaitForTarget("any", 3):

    if not API.StopRequested:

        API.SysMsg(
            "Shovel did not produce a target cursor!",
            33
        )

    API.Stop()
    raise SystemExit


# ------------------------------------------------------------
# TARGET TREASURE MAP
# ------------------------------------------------------------

API.Target(treasure_map.Serial)


# ------------------------------------------------------------
# WAIT FOR LOCATION TARGET
# ------------------------------------------------------------

if not API.WaitForTarget("any", 3):

    if not API.StopRequested:

        API.SysMsg(
            "No second target cursor appeared!",
            33
        )

    API.Stop()
    raise SystemExit


# ------------------------------------------------------------
# TARGET SELF
# ------------------------------------------------------------

API.TargetSelf()

API.SysMsg(
    "Treasure map targeted.",
    68
)

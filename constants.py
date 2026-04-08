"""
constants.py — all settings for GetPackets.
Change MAX_PACKETS to collect more or fewer PDFs per run.
"""

MAX_PACKETS        = 1000      # stop downloading PDFs after this many
MAX_PLACES         = 3000     # how many municipalities to load
MIN_POPULATION     = 5000     # skip tiny places below this population

import os as _os
_ROOT       = _os.path.dirname(_os.path.abspath(__file__))
PACKETS_DIR = _os.path.join(_ROOT, "data", "packets")
DB_FILE     = _os.path.join(_ROOT, "data", "db", "agenda.db")
CITIES_CSV         = "data/uscities.csv"
CITIES_CSV_URL     = "https://simplemaps.com/static/exports/us-cities/1.79/us-cities.csv"

REQUEST_TIMEOUT    = 15   # seconds — loading a webpage
DOWNLOAD_TIMEOUT   = 60   # seconds — downloading a PDF
FINDER_TIMEOUT     = 3    # seconds — probing URL patterns (keep short)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Body types collected ─────────────────────────────────────────────────────
# Any meeting body whose name matches ANY keyword below will be collected.
TARGET_BODIES = {

    # City / Town / County governing bodies
    "city_council": [
        "city council", "town council", "village board", "borough council",
        "county council", "board of trustees", "town board", "common council",
        "board of commissioners", "county commission", "county board",
        "selectboard", "selectmen", "aldermen", "board of aldermen",
        "township board", "township council", "board of supervisors",
        "city commission", "metro council", "metropolitan council",
        "parish council", "parish commission", "parish board",
        "borough assembly", "city assembly", "town meeting",
        "village council", "village commission",
        "county court", "quorum court",
        "city legislature", "city legislative",
        "governing body", "governing board",
    ],

    # Planning & Zoning
    "planning_zoning": [
        "planning commission", "planning and zoning", "planning & zoning",
        "zoning commission", "planning board", "land use commission",
        "land use board", "land use committee", "land use review",
        "land use and neighborhoods", "development review",
        "development review board", "development review committee",
        "planning committee", "planning department", "planning division",
        "planning advisory", "planning agency", "planning council",
        "planning authority", "city planning", "town planning",
        "county planning", "metropolitan planning", "regional planning",
        "comprehensive plan", "general plan", "comp plan",
        "community development commission", "community development committee",
        "community development board", "community development department",
        "growth management", "urban planning", "urban design",
        "urban development", "urban affairs", "neighborhood planning",
        "area planning", "site plan", "site review", "site committee",
        "subdivision committee", "subdivision review", "subdivision board",
        "built environment", "built environment committee",
        "hearing examiner", "land use hearing",
        "development services", "development services board",
        "community planning", "long range planning", "current planning",
        "zoning and planning", "planning and development",
        "planning and building", "zoning and land use",
    ],

    # Zoning Board of Adjustments / Appeals / Variances
    "board_of_adjustments": [
        "board of adjustment", "board of zoning adjustment",
        "zoning board of adjustment", "zoning adjustment",
        "variance board", "adjustment board",
        "board of zoning appeals", "zoning board of appeals",
        "zoning appeals", "zoning board", "zoning hearing board",
        "zoning hearing officer", "zoning committee", "zoning commission",
        "variance committee", "variance hearing", "exception committee",
        "special exception", "conditional use", "conditional use board",
        "special use permit", "special use committee",
        "rezoning committee", "rezoning board", "rezoning hearing",
    ],

    # Building & Construction Regulations
    "building_regulations": [
        "building board", "building commission", "building committee",
        "building department", "building code", "building codes board",
        "building inspection", "building inspector", "building official",
        "building standards", "building review", "building permit",
        "construction board", "construction committee",
        "construction review", "construction standards",
        "code enforcement", "code compliance", "code committee",
        "code board", "housing board", "housing commission",
        "housing committee", "housing authority", "housing and zoning",
        "housing code", "housing standards", "property maintenance",
        "property standards", "nuisance abatement",
        "electrical board", "plumbing board", "mechanical board",
        "fire code", "fire prevention", "fire marshal",
        "structural board", "structural review",
        "floodplain", "flood plain", "stormwater", "storm water",
        "grading committee", "grading board",
        "right of way", "right-of-way", "encroachment",
    ],

    # Historic Preservation & Design Review
    "historic_commission": [
        "historic", "historical commission", "heritage commission",
        "heritage board", "landmarks commission", "landmark board",
        "landmark committee", "landmark preservation",
        "historic preservation", "historic district", "historic review",
        "architectural review", "architectural review board",
        "architectural review committee", "design review",
        "design review board", "design review committee",
        "design standards", "aesthetic review", "appearance commission",
        "appearance review board", "conservation commission",
        "conservation board", "conservation district",
    ],

    # Board of Appeals
    "board_of_appeals": [
        "board of appeals", "appeals board", "appeals committee",
        "building board of appeals", "building appeals",
        "construction board of appeals", "construction appeals",
        "code appeals", "code board of appeals",
        "housing appeals", "housing board of appeals",
        "zoning appeals board", "development appeals",
        "adjustment and appeals", "board of review",
    ],

    # Environmental & Sustainability
    "environmental_board": [
        "environmental commission", "environmental committee",
        "environmental board", "environmental review",
        "environmental advisory", "environmental quality",
        "sustainability commission", "sustainability committee",
        "sustainability board", "green building",
        "tree board", "tree commission", "tree committee",
        "urban forestry", "open space", "parks and open space",
        "greenway", "wetlands", "wetland review", "watershed",
        "natural resources", "environmental impact",
    ],

    # Subdivision & Platting
    "subdivision_platting": [
        "plat", "platting", "plat committee", "plat board",
        "plat review", "plat commission", "subdivision",
        "subdivision plat", "lot split", "lot line", "lot division",
        "replat", "minor plat", "major plat",
        "preliminary plat", "final plat", "short plat",
        "short subdivision", "long plat", "long subdivision",
        "boundary line adjustment", "lot consolidation",
        "dedication", "easement review", "annexation",
        "annexation committee", "deannexation",
    ],

    # Redevelopment & Economic Development
    "redevelopment": [
        "redevelopment", "redevelopment authority",
        "redevelopment commission", "redevelopment agency",
        "community redevelopment", "urban redevelopment",
        "economic development", "economic development commission",
        "economic development committee", "economic development board",
        "downtown development", "downtown authority",
        "tax increment", "tax increment financing", "tif",
        "enterprise zone", "empowerment zone",
        "housing redevelopment", "blight", "blighted",
        "renewal", "urban renewal",
    ],

    # Transportation & Infrastructure (land use related)
    "transportation": [
        "transportation commission", "transportation committee",
        "transportation board", "traffic commission",
        "traffic committee", "traffic board",
        "roads commission", "roads committee",
        "infrastructure committee", "infrastructure board",
        "public works commission", "public works committee",
        "utilities commission", "utilities committee",
        "water board", "water commission", "sewer board",
        "sewer commission", "transit commission",
    ],

    # Special / Advisory Boards (land use related)
    "advisory_board": [
        "advisory board", "advisory committee", "advisory commission",
        "citizens advisory", "citizen advisory",
        "technical advisory", "technical review",
        "technical review committee", "staff review",
        "development committee", "review board",
        "review committee", "review commission",
        "steering committee", "task force",
        "oversight committee", "oversight board",
    ],


    # Planning & Zoning — core
    "planning_zoning": [
        "planning commission", "planning and zoning", "planning & zoning",
        "zoning commission", "planning board", "land use commission",
        "land use and neighborhoods", "land use committee",
        "built environment", "built environment committee",
        "hearing examiner", "land use hearing",
        "comprehensive plan", "comp plan",
        "neighborhood committee", "neighborhoods committee",
        "development services", "development services board",
        "community planning", "community development",
        "long range planning", "current planning",
        "zoning and planning", "planning and development",
        "planning and building",
        "land use board", "land use committee", "land use review",
        "development review", "development review board",
        "development review committee", "planning committee",
        "planning department", "planning division",
        "planning advisory", "planning agency",
        "planning council", "planning authority",
        "city planning", "town planning", "county planning",
        "metropolitan planning", "regional planning",
        "comprehensive plan", "general plan",
        "community development commission",
        "community development committee",
        "community development board",
        "community development department",
        "growth management",
        "urban planning", "urban design",
        "urban development", "urban affairs",
        "neighborhood planning", "area planning",
        "site plan", "site review", "site committee",
        "subdivision committee", "subdivision review",
        "subdivision board",
    ],

    # Zoning Board of Adjustments / Appeals / Variances
    "board_of_adjustments": [
        "board of adjustment", "board of zoning adjustment",
        "zoning board of adjustment", "zoning adjustment",
        "variance board", "adjustment board",
        "board of zoning appeals", "zoning board of appeals",
        "zoning appeals", "zoning board",
        "zoning hearing board", "zoning hearing officer",
        "zoning committee", "zoning commission",
        "variance committee", "variance hearing",
        "exception committee", "special exception",
        "conditional use", "conditional use board",
        "special use permit", "special use committee",
        "rezoning committee", "rezoning board",
        "rezoning hearing",
    ],

    # Building & Construction
    "building_regulations": [
        "building board", "building commission",
        "building committee", "building department",
        "building code", "building codes board",
        "building inspection", "building inspector",
        "building official", "building standards",
        "building review", "building permit",
        "construction board", "construction committee",
        "construction review", "construction standards",
        "code enforcement", "code compliance",
        "code committee", "code board",
        "housing board", "housing commission",
        "housing committee", "housing authority",
        "housing and zoning",
        "housing code", "housing standards",
        "property maintenance", "property standards",
        "nuisance abatement",
        "electrical board", "electrical commission",
        "plumbing board", "plumbing commission",
        "mechanical board", "fire code",
        "fire prevention", "fire marshal",
        "structural board", "structural review",
        "floodplain", "flood plain",
        "stormwater", "storm water",
        "grading committee", "grading board",
        "right of way", "right-of-way",
        "encroachment",
    ],

    # Historic Preservation (affects building regulations)
    "historic_commission": [
        "historic", "historical commission",
        "heritage commission", "heritage board",
        "landmarks commission", "landmark board",
        "landmark committee", "landmark preservation",
        "historic preservation", "historic district",
        "historic review", "architectural review",
        "architectural review board", "architectural review committee",
        "design review", "design review board",
        "design review committee", "design standards",
        "aesthetic review", "appearance commission",
        "appearance review board",
        "conservation commission", "conservation board",
        "conservation district",
    ],

    # Board of Appeals (building/code related)
    "board_of_appeals": [
        "board of appeals", "appeals board", "appeals committee",
        "building board of appeals", "building appeals",
        "construction board of appeals", "construction appeals",
        "code appeals", "code board of appeals",
        "housing appeals", "housing board of appeals",
        "zoning appeals board",
        "development appeals",
    ],

    # Environmental / Sustainability (affects land use)
    "environmental_board": [
        "environmental commission", "environmental committee",
        "environmental board", "environmental review",
        "environmental advisory", "environmental quality",
        "sustainability commission", "sustainability committee",
        "sustainability board", "green building",
        "tree board", "tree commission", "tree committee",
        "urban forestry", "open space",
        "parks and open space", "greenway",
        "wetlands", "wetland review",
        "watershed", "natural resources",
        "environmental impact",
    ],

    # Subdivision & Platting
    "subdivision_platting": [
        "plat", "platting", "plat committee", "plat board",
        "plat review", "plat commission",
        "subdivision", "subdivision plat",
        "lot split", "lot line", "lot division",
        "replat", "minor plat", "major plat",
        "preliminary plat", "final plat",
        "short plat", "short subdivision",
        "long plat", "long subdivision",
        "boundary line adjustment",
        "lot consolidation",
        "dedication", "easement review",
        "annexation", "annexation committee",
        "deannexation",
    ],
}

# Flat list of all keywords for fast search inside PDFs
ALL_PLANNING_KEYWORDS = [
    # Rezoning
    "rezoning", "rezone", "zone change", "zoning change",
    "zoning amendment", "text amendment", "map amendment",
    "zoning map", "zoning ordinance",
    # Variance
    "variance", "variances", "dimensional variance",
    "use variance", "area variance",
    # Special use / conditional use
    "special use permit", "conditional use permit", "cup",
    "special exception", "special use",
    # Subdivision / Plat
    "subdivision", "plat", "platting", "replat",
    "preliminary plat", "final plat", "short plat",
    "lot split", "lot line adjustment", "boundary line",
    "annexation", "deannexation",
    # Site plan
    "site plan", "site plan review", "site plan approval",
    "site development", "development plan",
    # Building / permits
    "building permit", "construction permit", "demolition permit",
    "grading permit", "excavation permit",
    "certificate of occupancy", "occupancy permit",
    # Appeals
    "appeal", "board of appeals", "zoning appeal",
    "building appeal", "code appeal",
    # Environmental
    "environmental impact", "environmental review",
    "floodplain", "wetlands", "stormwater",
    # Historic
    "historic preservation", "landmark", "heritage",
    "architectural review", "design review",
    # General planning
    "comprehensive plan", "general plan", "master plan",
    "land use plan", "zoning code", "development agreement",
    "planned unit development", "pud",
    "overlay district", "overlay zone",
    "mixed use", "mixed-use",
    "affordable housing", "density bonus",
    "easement", "right of way", "dedication",
]

# URL patterns the finder tries.
# Placeholders replaced at runtime:
#   {name}    → city name, spaces→hyphens  e.g. "oak-park"
#   {name_}   → spaces→underscores         e.g. "oak_park"
#   {nameraw} → no separator               e.g. "oakpark"
#   {state}   → 2-letter abbreviation      e.g. "il"
MEETING_URL_PATTERNS = [
    # cityof... patterns
    "https://www.cityof{nameraw}.gov/government/city-council/agendas-minutes",
    "https://www.cityof{nameraw}.gov/agendas-minutes",
    "https://www.cityof{nameraw}.gov/agendas",
    "https://www.cityof{nameraw}.gov/meetings",
    "https://www.cityof{nameraw}.gov/council/meetings",
    "https://www.cityof{nameraw}.gov/city-council",
    "https://www.cityof{nameraw}.gov/government/meetings",
    # plain city name .gov
    "https://www.{name}.gov/agendas",
    "https://www.{name}.gov/meetings",
    "https://www.{name}.gov/council/agendas",
    "https://www.{name}.gov/city-council",
    "https://www.{name}.gov/government/agendas-minutes",
    "https://www.{name}.gov/agendas-minutes",
    # city.NAME.STATE.us
    "https://www.city.{name}.{state}.us/agendas",
    "https://www.city.{name}.{state}.us/meetings",
    "https://www.city.{name}.{state}.us/council",
    "https://www.city.{name}.{state}.us/government/agendas",
    # NAME.STATE.us
    "https://www.{name}.{state}.us/agendas",
    "https://www.{name}.{state}.us/meetings",
    "https://www.{name}.{state}.us/council",
    # NAME.STATE.gov
    "https://www.{name}.{state}.gov/agendas",
    "https://www.{name}.{state}.gov/meetings",
    # townof / villageof / boroughof
    "https://www.townof{nameraw}.gov/agendas",
    "https://www.townof{nameraw}.gov/meetings",
    "https://www.townof{nameraw}.gov/council",
    "https://www.villageof{nameraw}.gov/agendas",
    "https://www.villageof{nameraw}.gov/meetings",
    "https://www.boroughof{nameraw}.gov/agendas",
    "https://www.boroughof{nameraw}.gov/meetings",
    # bare name
    "https://{nameraw}.gov/agendas",
    "https://{nameraw}.gov/meetings",
    "https://{nameraw}.gov/council",
    # county patterns
    "https://www.{name}county.gov/agendas",
    "https://www.{name}county.gov/meetings",
    "https://www.co.{name}.{state}.us/agendas",
    "https://www.co.{name}.{state}.us/meetings",
    "https://www.co.{name}.{state}.us/boc",
]

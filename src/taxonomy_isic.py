"""
Hierarchical classification taxonomy based on the UN ISIC Rev. 5
(International Standard Industrial Classification of All Economic
Activities), https://unstats.un.org/unsd/classifications/Econ/

Two hierarchy levels are implemented, as required:
  Level 1: SECTIONS  (A ... V)
  Level 2: DIVISIONS (01 ... 99)

The division table below (_RAW_DIVISIONS) is the authoritative class
list and is parsed verbatim, so section letters and division names
exactly match the official classification.

Each division additionally carries a keyword lexicon (KEYWORDS) used by
the rule-based classifier in classifier.py. Keywords are matched (case-
insensitively, on word boundaries) against project metadata (title,
description, keywords) and base data (file names, readable file
content).
"""

# ---------------------------------------------------------------------------
# Level 1: ISIC Rev. 5 sections
# ---------------------------------------------------------------------------

SECTIONS: dict[str, str] = {
    "A": "Agriculture, forestry and fishing",
    "B": "Mining and quarrying",
    "C": "Manufacturing",
    "D": "Electricity, gas, steam and air conditioning supply",
    "E": "Water supply; sewerage, waste management and remediation activities",
    "F": "Construction",
    "G": "Wholesale and retail trade",
    "H": "Transportation and storage",
    "I": "Accommodation and food service activities",
    "J": ("Publishing, broadcasting, and content production and "
         "distribution activities"),
    "K": ("Telecommunication, computer programming, consultancy, computing "
         "infrastructure and other information service activities"),
    "L": "Financial and insurance activities",
    "M": "Real estate activities",
    "N": "Professional, scientific and technical activities",
    "O": "Administrative and support service activities",
    "P": "Public administration and defence; compulsory social security",
    "Q": "Education",
    "R": "Human health and social work activities",
    "S": "Arts, sports and recreation",
    "T": "Other service activities",
    "U": ("Activities of households as employers; undifferentiated goods- "
         "and services-producing activities of households for own use"),
    "V": "Activities of extraterritorial organizations and bodies",
}

# ---------------------------------------------------------------------------
# Level 2: ISIC Rev. 5 divisions (authoritative list, parsed verbatim)
# Format per line:  <SectionLetter><DivisionCode> - <DivisionCode> - <Name>
# ---------------------------------------------------------------------------

_RAW_DIVISIONS = """\
A01 - 01 - Crop and animal production, hunting and related service activities
A02 - 02 - Forestry and logging
A03 - 03 - Fishing and aquaculture
B05 - 05 - Mining of coal and lignite
B06 - 06 - Extraction of crude petroleum and natural gas
B07 - 07 - Mining of metal ores
B08 - 08 - Other mining and quarrying
B09 - 09 - Mining support service activities
C10 - 10 - Manufacture of food products
C11 - 11 - Manufacture of beverages
C12 - 12 - Manufacture of tobacco products
C13 - 13 - Manufacture of textiles
C14 - 14 - Manufacture of wearing apparel
C15 - 15 - Manufacture of leather and related products
C16 - 16 - Manufacture of wood and of products of wood and cork, except furniture; manufacture of articles of straw and plaiting materials
C17 - 17 - Manufacture of paper and paper products
C18 - 18 - Printing and reproduction of recorded media
C19 - 19 - Manufacture of coke and refined petroleum products
C20 - 20 - Manufacture of chemicals and chemical products
C21 - 21 - Manufacture of basic pharmaceutical products and pharmaceutical preparations
C22 - 22 - Manufacture of rubber and plastic products
C23 - 23 - Manufacture of other non-metallic mineral products
C24 - 24 - Manufacture of basic metals
C25 - 25 - Manufacture of fabricated metal products, except machinery and equipment
C26 - 26 - Manufacture of computer, electronic and optical products
C27 - 27 - Manufacture of electrical equipment
C28 - 28 - Manufacture of machinery and equipment n.e.c.
C29 - 29 - Manufacture of motor vehicles, trailers and semi-trailers
C30 - 30 - Manufacture of other transport equipment
C31 - 31 - Manufacture of furniture
C32 - 32 - Other manufacturing
C33 - 33 - Repair, maintenance and installation of machinery and equipment
D35 - 35 - Electricity, gas, steam and air conditioning supply
E36 - 36 - Water collection, treatment and supply
E37 - 37 - Sewerage
E38 - 38 - Waste collection, treatment and disposal, and recovery activities
E39 - 39 - Remediation and other waste management service activities
F41 - 41 - Construction of residential and non-residential buildings
F42 - 42 - Civil engineering
F43 - 43 - Specialized construction activities
G46 - 46 - Wholesale trade
G47 - 47 - Retail trade
H49 - 49 - Land transport and transport via pipelines
H50 - 50 - Water transport
H51 - 51 - Air transport
H52 - 52 - Warehousing and support activities for transportation
H53 - 53 - Postal and courier activities
I55 - 55 - Accommodation
I56 - 56 - Food and beverage service activities
J58 - 58 - Publishing activities
J59 - 59 - Motion picture, video and television programme production, sound recording and music publishing activities
J60 - 60 - Programming, broadcasting, news agency and other content distribution activities
K61 - 61 - Telecommunications
K62 - 62 - Computer programming, consultancy and related activities
K63 - 63 - Computing infrastructure, data processing, hosting, and other information service activities
L64 - 64 - Financial service activities, except insurance and pension funding
L65 - 65 - Insurance, reinsurance and pension funding, except compulsory social security
L66 - 66 - Activities auxiliary to financial service and insurance activities
M68 - 68 - Real estate activities
N69 - 69 - Legal and accounting activities
N70 - 70 - Activities of head offices; management consultancy activities
N71 - 71 - Architectural and engineering activities; technical testing and analysis
N72 - 72 - Scientific research and development
N73 - 73 - Activities of advertising, market research and public relations
N74 - 74 - Other professional, scientific and technical activities
N75 - 75 - Veterinary activities
O77 - 77 - Rental and leasing activities
O78 - 78 - Employment activities
O79 - 79 - Travel agency, tour operator, and other travel related activities
O80 - 80 - Investigation and security activities
O81 - 81 - Services to buildings and landscape activities
O82 - 82 - Office administrative, office support and other business support activities
P84 - 84 - Public administration and defence; compulsory social security
Q85 - 85 - Education
R86 - 86 - Human health activities
R87 - 87 - Residential care activities
R88 - 88 - Social work activities without accommodation
S90 - 90 - Arts creation and performing arts activities
S91 - 91 - Library, archives, museum and other cultural activities
S92 - 92 - Gambling and betting activities
S93 - 93 - Sports activities and amusement and recreation activities
T94 - 94 - Activities of membership organizations
T95 - 95 - Repair and maintenance of computers, personal and household goods, and motor vehicles and motorcycles
T96 - 96 - Personal service activities
U97 - 97 - Activities of households as employers of domestic personnel
U98 - 98 - Undifferentiated goods- and services-producing activities of private households for own use
V99 - 99 - Activities of extraterritorial organizations and bodies
"""

# ---------------------------------------------------------------------------
# Keyword lexicon per division (used by the classifier and as search tags)
# ---------------------------------------------------------------------------

KEYWORDS: dict[str, list[str]] = {
    "01": ["agriculture", "farming", "farm", "farmer", "crop", "livestock",
           "cattle", "harvest", "agricultural", "smallholder", "maize",
           "wheat", "dairy", "poultry", "irrigation", "agrarian",
           "horticulture", "hunting"],
    "02": ["forestry", "forest", "logging", "timber", "deforestation",
           "woodland", "silviculture"],
    "03": ["fishing", "fishery", "fisheries", "aquaculture", "fisher",
           "marine harvest", "fish farming"],
    "05": ["coal", "lignite", "coal mining", "colliery"],
    "06": ["petroleum", "crude oil", "natural gas", "oil extraction",
           "oil and gas", "oilfield"],
    "07": ["metal ore", "iron ore", "gold mining", "copper mining",
           "platinum", "ore"],
    "08": ["quarry", "quarrying", "sand mining", "gravel", "stone extraction"],
    "09": ["mining support", "drilling service", "mine service", "mining",
           "miner", "mineworker"],
    "10": ["food production", "food processing", "food manufacturing",
           "food industry", "meat processing", "bakery"],
    "11": ["beverage", "brewery", "winery", "distillery", "soft drink"],
    "12": ["tobacco", "cigarette manufacturing"],
    "13": ["textile", "weaving", "spinning", "fabric"],
    "14": ["apparel", "garment", "clothing manufacture", "tailoring"],
    "15": ["leather", "footwear", "tannery"],
    "16": ["sawmill", "wood product", "carpentry", "plywood"],
    "17": ["paper mill", "pulp and paper", "paper product"],
    "18": ["printing", "print shop", "reproduction of media"],
    "19": ["refinery", "refined petroleum", "coke oven"],
    "20": ["chemical industry", "chemical manufacturing",
           "fertilizer production", "petrochemical"],
    "21": ["pharmaceutical", "pharma", "drug manufacturing",
           "medicine production", "vaccine production"],
    "22": ["rubber", "plastics manufacturing", "plastic product"],
    "23": ["cement", "ceramics", "glass manufacturing", "concrete"],
    "24": ["steel", "smelting", "metallurgy", "foundry"],
    "25": ["metal fabrication", "metalwork", "welding"],
    "26": ["electronics manufacturing", "semiconductor", "optical products",
           "computer hardware"],
    "27": ["electrical equipment", "electric motor", "battery production"],
    "28": ["machinery", "industrial equipment", "machine tools"],
    "29": ["automotive", "car manufacturing", "vehicle assembly",
           "motor vehicle"],
    "30": ["shipbuilding", "aircraft manufacturing", "rolling stock"],
    "31": ["furniture"],
    "32": ["manufacturing", "factory", "industrial production"],
    "33": ["machine repair", "equipment installation",
           "industrial maintenance"],
    "35": ["electricity", "power supply", "energy supply", "power grid",
           "power plant", "renewable energy", "solar power", "wind power",
           "electrification", "energy access", "load shedding"],
    "36": ["water supply", "drinking water", "water access",
           "water treatment", "water provision", "tap water"],
    "37": ["sewerage", "sewage", "wastewater"],
    "38": ["waste management", "recycling", "waste disposal", "solid waste",
           "landfill", "waste picker"],
    "39": ["remediation", "decontamination", "pollution cleanup"],
    "41": ["construction", "building construction", "housing construction"],
    "42": ["civil engineering", "infrastructure project", "road construction",
           "bridge construction"],
    "43": ["plumbing", "electrical installation", "demolition",
           "construction worker"],
    "46": ["wholesale", "distributor", "wholesaler"],
    "47": ["retail", "shop", "store", "consumer", "shopping", "market trader",
           "informal trading", "spaza", "vendor", "e-commerce", "supermarket",
           "car dealership"],
    "49": ["transport", "public transport", "taxi", "bus", "railway",
           "commuting", "minibus", "road transport", "mobility"],
    "50": ["shipping", "maritime transport", "ferry"],
    "51": ["airline", "air transport", "aviation"],
    "52": ["logistics", "warehouse", "freight", "supply chain"],
    "53": ["postal", "courier", "mail delivery"],
    "55": ["hotel", "accommodation", "hostel", "lodging", "guesthouse"],
    "56": ["restaurant", "catering", "food service", "cafe", "street food",
           "food security", "nutrition", "food consumption", "diet", "eating"],
    "58": ["publishing", "publisher", "newspaper", "journalism", "media house",
           "book publishing"],
    "59": ["film", "television production", "video production", "documentary",
           "sound recording", "music production"],
    "60": ["broadcasting", "radio station", "tv channel", "news agency",
           "streaming platform", "content distribution"],
    "61": ["telecommunication", "mobile phone", "internet access", "broadband",
           "connectivity", "mobile network", "cellphone"],
    "62": ["software", "programming", "software development", "coding",
           "app development", "information technology", "ict",
           "digital technology", "artificial intelligence",
           "machine learning", "computing"],
    "63": ["data processing", "web portal", "information service",
           "social media", "online platform", "digital platform",
           "internet use", "digital media", "cloud computing", "hosting",
           "data center", "data centre"],
    "64": ["banking", "bank", "credit", "loan", "microfinance",
           "financial inclusion", "savings", "fintech", "finance",
           "financial service", "money"],
    "65": ["insurance", "pension", "life insurance", "insurer"],
    "66": ["stock exchange", "brokerage", "asset management",
           "investment fund"],
    "68": ["real estate", "housing market", "rental housing", "property",
           "landlord", "tenant", "housing", "informal settlement", "eviction",
           "homeownership"],
    "69": ["legal", "law firm", "lawyer", "accounting", "audit",
           "justice system", "legal aid", "court"],
    "70": ["management consulting", "business strategy", "consultancy",
           "corporate governance"],
    "71": ["architecture", "engineering", "urban planning",
           "technical testing", "surveying", "urban design"],
    "72": ["research", "scientific research", "science", "researcher",
           "study", "qualitative research", "quantitative research", "survey",
           "experiment", "fieldwork", "interview", "focus group",
           "ethnography", "case study", "data collection", "social science",
           "laboratory", "r&d", "academic research", "dataset", "methodology"],
    "73": ["advertising", "marketing", "market research",
           "public opinion polling", "opinion poll", "branding",
           "public relations"],
    "74": ["design services", "photography", "translation",
           "interpretation services"],
    "75": ["veterinary", "animal health", "vet clinic"],
    "77": ["rental service", "leasing", "equipment rental"],
    "78": ["employment", "labour market", "labor market", "recruitment",
           "unemployment", "job seeking", "job creation", "labour force",
           "workforce", "informal employment", "precarious work",
           "gig economy"],
    "79": ["tourism", "travel agency", "tour operator", "tourist"],
    "80": ["private security", "security guard", "surveillance",
           "investigation service"],
    "81": ["cleaning services", "landscaping", "facility management"],
    "82": ["call centre", "call center", "office support",
           "business process outsourcing"],
    "84": ["government", "public administration", "policy", "public policy",
           "municipality", "governance", "election", "voting", "democracy",
           "political", "politics", "state", "defence", "defense", "military",
           "police", "policing", "social security", "social grant",
           "welfare state", "public service", "civil service", "regulation",
           "local government", "parliament", "citizenship", "migration",
           "immigration", "refugee", "asylum"],
    "85": ["education", "school", "student", "teacher", "learning",
           "university", "higher education", "curriculum", "classroom",
           "learner", "teaching", "pedagogy", "literacy", "training",
           "e-learning", "college", "pupil", "educational", "academic",
           "schooling", "kindergarten", "preschool", "tuition", "matric",
           "graduate", "undergraduate", "postgraduate", "dissertation",
           "thesis", "lecturer", "faculty", "stem education"],
    "86": ["health", "healthcare", "hospital", "clinic", "medical", "patient",
           "nurse", "doctor", "disease", "illness", "hiv", "aids",
           "tuberculosis", "covid", "pandemic", "epidemic", "mental health",
           "public health", "vaccination", "treatment", "therapy", "medicine",
           "maternal health", "reproductive health", "diagnosis",
           "health care", "wellbeing", "well-being", "disability",
           "chronic disease", "cancer", "diabetes"],
    "87": ["residential care", "nursing home", "care home", "elderly care",
           "care facility"],
    "88": ["social work", "social worker", "child care", "childcare",
           "community development", "social services", "counselling",
           "counseling", "family support", "child protection",
           "community support", "ngo", "humanitarian"],
    "90": ["art", "artist", "creative", "theatre", "theater", "performance",
           "music", "dance", "literature", "poetry", "cultural production",
           "visual arts", "performing arts"],
    "91": ["library", "archive", "museum", "heritage", "cultural heritage",
           "curation", "collection", "archival"],
    "92": ["gambling", "betting", "casino", "lottery"],
    "93": ["sport", "sports", "recreation", "fitness", "football", "soccer",
           "athletics", "physical activity", "leisure", "exercise"],
    "94": ["trade union", "union", "religious organization", "church",
           "religion", "religious", "civil society", "association",
           "advocacy", "activism", "social movement", "faith",
           "political party", "mosque", "congregation"],
    "95": ["computer repair", "phone repair", "appliance repair",
           "vehicle repair", "car repair", "motorcycle repair"],
    "96": ["hairdressing", "beauty salon", "funeral services",
           "personal services", "domestic services", "laundry"],
    "97": ["domestic worker", "domestic labour", "domestic labor",
           "household employment", "housekeeper", "nanny"],
    "98": ["subsistence", "household production", "own-use production",
           "household", "family life", "everyday life", "daily life"],
    "99": ["united nations", "world bank", "international organization",
           "international organisation", "embassy", "diplomatic", "unicef",
           "unesco", "who", "imf", "foreign aid", "development aid",
           "international development"],
}

# ---------------------------------------------------------------------------
# Parse the authoritative list into the DIVISIONS structure
# ---------------------------------------------------------------------------


def _parse_divisions(raw: str) -> dict[str, dict]:
    divisions: dict[str, dict] = {}
    for line in raw.strip().splitlines():
        combined, code, name = (part.strip() for part in line.split(" - ", 2))
        section = combined[0]
        assert combined == f"{section}{code}", f"inconsistent line: {line}"
        divisions[code] = {
            "section": section,
            "name": name,
            "keywords": KEYWORDS.get(code, []),
        }
    return divisions


DIVISIONS: dict[str, dict] = _parse_divisions(_RAW_DIVISIONS)


def full_class_name(division_code: str) -> str:
    """Return the full human-readable class name for a division, e.g.
    'Q85 - Education' -> used as bin names in the report histograms."""
    div = DIVISIONS.get(division_code)
    if not div:
        return division_code
    return f"{div['section']}{division_code} \u2013 {div['name']}"


def section_name(section_code: str) -> str:
    return SECTIONS.get(section_code, section_code)
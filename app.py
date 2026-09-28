import os
import re
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from langchain_google_genai import ChatGoogleGenerativeAI


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

KNOWLEDGE_FILE = DATA_DIR / "college_info.txt"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)
CORS(app)


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

if not KNOWLEDGE_FILE.exists():
    raise FileNotFoundError(
        f"Knowledge base not found: {KNOWLEDGE_FILE}"
    )

with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
    KNOWLEDGE_TEXT = file.read()


# ============================================================
# STANDARD "NOT FOUND" MESSAGE (used everywhere, consistently)
# ============================================================

NOT_FOUND_MESSAGE = (
    "I don't have that information in the current "
    "CampusMate knowledge base."
)


# ============================================================
# MAIN SECTION NUMBERS
# ============================================================

# IMPORTANT:
# Only these 35 numbered headings are treated as sections.
# Numbered items inside a section remain part of that section.

MAIN_SECTION_HEADINGS = {
    1: "COLLEGE OVERVIEW",
    2: "VISION AND MISSION",
    3: "PRINCIPAL",
    4: "CURRENT ACADEMIC COUNCIL / SENIOR ACADEMIC ROLES",
    5: "COURSES OFFERED",
    6: "COMPUTER SCIENCE AND ENGINEERING",
    7: "INFORMATION TECHNOLOGY",
    8: "ARTIFICIAL INTELLIGENCE AND DATA SCIENCE",
    9: "ELECTRONICS AND COMMUNICATION ENGINEERING",
    10: "ELECTRICAL AND ELECTRONICS ENGINEERING",
    11: "MECHANICAL ENGINEERING",
    12: "CIVIL ENGINEERING",
    13: "SCIENCE AND HUMANITIES",
    14: "CENTRAL LIBRARY",
    15: "INTERNET AND COMPUTING FACILITIES",
    16: "INFRASTRUCTURE",
    17: "HOSTEL",
    18: "SPORTS",
    19: "TRANSPORT",
    20: "TRAINING AND PLACEMENT",
    21: "RESEARCH AND DEVELOPMENT",
    22: "INNOVATION / HACKATHONS / PROJECT ACTIVITIES",
    23: "CLUBS AND STUDENT ACTIVITIES",
    24: "SCHOLARSHIPS",
    25: "ALUMNI",
    26: "E-LEARNING AND DIGITAL RESOURCES",
    27: "PROFESSIONAL DEVELOPMENT",
    28: "RECENT / CURRENT ANNOUNCEMENTS",
    29: "NAAC / IQAC / QUALITY INFORMATION",
    30: "STUDENT SUPPORT",
    31: "IMPORTANT STUDENT-HANDBOOK AREAS",
    32: "CAMPUS AMENITIES",
    33: "CONTACT INFORMATION",
    34: "CAMPUSMATE ANSWERING RULES",
    35: "EXAMPLE QUESTIONS CAMPUSMATE SHOULD HANDLE",
}


# ============================================================
# KNOWLEDGE BASE SPLITTER
# ============================================================

def split_knowledge_base(text):

    lines = text.splitlines()

    sections = []

    current_number = None
    current_title = None
    current_lines = []

    for line in lines:

        stripped = line.strip()

        match = re.match(
            r"^(\d+)\.\s*(.*)$",
            stripped
        )

        if match:

            number = int(match.group(1))
            title = match.group(2).strip()

            # Only numbers 1-35 with the expected main heading
            # can start a new section.
            if (
                number in MAIN_SECTION_HEADINGS
                and title.upper() == MAIN_SECTION_HEADINGS[number]
            ):

                if current_number is not None:

                    sections.append({
                        "number": current_number,
                        "title": current_title,
                        "text": "\n".join(
                            current_lines
                        ).strip()
                    })

                current_number = number
                current_title = MAIN_SECTION_HEADINGS[number]
                current_lines = [stripped]

                continue

        # Every other line belongs to the current section.
        # This includes:
        #
        # 1. B.E. Civil Engineering
        # 2. B.E. Computer Science and Engineering
        #
        # and faculty/research numbered lists.

        if current_number is not None:
            current_lines.append(line)

    # Save final section
    if current_number is not None:

        sections.append({
            "number": current_number,
            "title": current_title,
            "text": "\n".join(
                current_lines
            ).strip()
        })

    return sections


KB_SECTIONS = split_knowledge_base(KNOWLEDGE_TEXT)


# ============================================================
# STARTUP INFORMATION
# ============================================================

print("=" * 60)
print("CAMPUSMATE STARTING")
print("=" * 60)

print(
    "Knowledge base sections found:",
    len(KB_SECTIONS)
)

print(
    "Knowledge base characters:",
    len(KNOWLEDGE_TEXT)
)

print("=" * 60)


# ============================================================
# SECTION FUNCTIONS
# ============================================================

def get_section(number):

    for section in KB_SECTIONS:

        if section["number"] == number:
            return section["text"]

    return ""


def get_sections(numbers):

    result = []

    for number in numbers:

        section = get_section(number)

        if section:
            result.append(section)

    return "\n\n".join(result)


# ============================================================
# CATEGORY MAPPING
# ============================================================

CATEGORY_SECTIONS = {

    "location": [1, 33],
    "overview": [1],
    "vision": [2],
    "principal": [3],
    "academic": [4],

    "courses": [5],

    "cse": [6],
    "it": [7],
    "ai": [8],
    "ece": [9],
    "eee": [10],
    "mechanical": [11],
    "civil": [12],

    "science": [13],
    "library": [14],
    "internet": [15],
    "infrastructure": [16],
    "hostel": [17],
    "sports": [18],
    "transport": [19],
    "placement": [20],
    "research": [21],
    "innovation": [22],
    "clubs": [23],
    "scholarship": [24],
    "alumni": [25],
    "elearning": [26],
    "professional": [27],
    "announcements": [28],
    "naac": [29],
    "support": [30],
    "handbook": [31],
    "amenities": [32],
    "contact": [33],
}


# ============================================================
# KEYWORDS
# ============================================================

CATEGORY_KEYWORDS = {

    "location": [
        "where",
        "located",
        "location",
        "address",
        "situated",
        "campus location",
        "college location",
        "college address",
    ],

    "principal": [
        "principal",
        "head of college",
    ],

    "courses": [
        "course",
        "courses",
        "program",
        "programs",
        "programme",
        "programmes",
        "degree",
        "degrees",
        "offered",
        "available",
        "b.e",
        "b.tech",
        "m.e",
        "mba",
        "phd",
    ],

    "cse": [
        "cse",
        "computer science",
        "computer science engineering",
    ],

    "it": [
        "information technology",
        "it department",
    ],

    "ai": [
        "artificial intelligence",
        "data science",
        "ai and ds",
    ],

    "ece": [
        "ece",
        "electronics and communication",
    ],

    "eee": [
        "eee",
        "electrical and electronics",
    ],

    "mechanical": [
        "mechanical",
        "mechanical engineering",
    ],

    "civil": [
        "civil",
        "civil engineering",
    ],

    "library": [
        "library",
        "books",
        "journal",
        "journals",
        "reading room",
        "opac",
        "delnet",
    ],

    "internet": [
        "internet",
        "wifi",
        "wi-fi",
        "computer",
        "computers",
        "lan",
        "network",
    ],

    "infrastructure": [
        "infrastructure",
        "classroom",
        "auditorium",
        "building",
        "facilities",
    ],

    "hostel": [
        "hostel",
        "hostels",
        "mess",
        "boys hostel",
        "girls hostel",
    ],

    "sports": [
        "sports",
        "sport",
        "cricket",
        "football",
        "basketball",
        "volleyball",
        "badminton",
        "tennis",
        "gym",
        "chess",
        "carrom",
    ],

    "transport": [
        "transport",
        "bus",
        "buses",
        "college bus",
        "bus facility",
        "bus route",
        "bus routes",
    ],

    "placement": [
        "placement",
        "placements",
        "job",
        "jobs",
        "recruitment",
        "career",
        "training and placement",
    ],

    "research": [
        "research",
        "r&d",
        "research development",
        "funded project",
    ],

    "innovation": [
        "innovation",
        "hackathon",
        "hackathons",
        "project expo",
        "projects",
        "sih",
    ],

    "clubs": [
        "club",
        "clubs",
        "ncc",
        "nss",
        "ieee",
        "iste",
        "iei",
        "iete",
        "student activities",
    ],

    "scholarship": [
        "scholarship",
        "scholarships",
        "fee waiver",
        "financial assistance",
        "award",
        "awards",
    ],

    "alumni": [
        "alumni",
        "former students",
    ],

    "elearning": [
        "e-learning",
        "elearning",
        "online learning",
        "swayam",
        "nptel",
        "digital resources",
    ],

    "professional": [
        "professional development",
        "soft skills",
        "aptitude",
        "communication training",
        "workshop",
        "fdp",
        "conference",
    ],

    "announcements": [
        "announcement",
        "announcements",
        "recent",
        "latest",
        "current",
        "event",
        "events",
    ],

    "naac": [
        "naac",
        "iqac",
        "accreditation",
        "quality",
    ],

    "support": [
        "student support",
        "support",
        "counselling",
        "student welfare",
    ],

    "handbook": [
        "handbook",
        "rules",
        "regulations",
    ],

    "amenities": [
        "amenities",
        "canteen",
        "cafeteria",
        "health centre",
        "medical",
        "recreation",
    ],

    "contact": [
        "contact",
        "phone",
        "telephone",
        "mobile",
        "email",
        "website",
    ],
}


# Friendly heading shown above each answer when a message
# contains MORE THAN ONE question (see split_multi_question below).
CATEGORY_LABELS = {
    "location": "📍 Location",
    "principal": "🎓 Principal",
    "courses": "📘 Courses",
    "cse": "💻 Computer Science and Engineering",
    "it": "💻 Information Technology",
    "ai": "🤖 AI & Data Science",
    "ece": "📡 Electronics and Communication",
    "eee": "⚡ Electrical and Electronics",
    "mechanical": "⚙️ Mechanical Engineering",
    "civil": "🏗️ Civil Engineering",
    "library": "📚 Library",
    "hostel": "🏠 Hostel",
    "sports": "🏅 Sports",
    "transport": "🚌 Transport",
    "placement": "💼 Placements",
    "scholarship": "🎗️ Scholarships",
    "contact": "📞 Contact",
    "academic": "🎓 Academic Council",
    "overview": "🏫 College Overview",
}


# ============================================================
# NORMALIZE QUESTION
# ============================================================

def normalize_question(question):

    q = str(question).lower().strip()

    q = re.sub(
        r"[^\w\s&.-]",
        " ",
        q
    )

    q = re.sub(
        r"\s+",
        " ",
        q
    )

    return q


# ============================================================
# WORD-BOUNDARY KEYWORD MATCHING
#
# Plain substring matching causes false positives - e.g. the
# word "transport" contains "sport" inside it, so a naive
# `"sport" in text` check would wrongly think a transport
# question is about sports. Matching on word boundaries avoids
# this whole class of bug.
# ============================================================

def keyword_matches(text, keyword):

    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text) is not None


# ============================================================
# DETECT CATEGORIES
# ============================================================

def detect_categories(question, previous_question=None):

    q = normalize_question(question)

    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword_matches(q, keyword.lower()):
                score += 1

        if score > 0:
            scores[category] = score

    categories = sorted(
        scores,
        key=scores.get,
        reverse=True
    )

    # FOLLOW-UP SUPPORT:
    # If the current question has no recognisable category at all
    # (e.g. "what is the intake?" with no department named), borrow
    # the category from the PREVIOUS question so short follow-up
    # questions still work.
    if not categories and previous_question:
        categories = detect_categories(previous_question)

    return categories


# ============================================================
# DEPARTMENT LOOKUP TABLES
# (small, clean, hand-checked data - used for short factual
#  follow-up answers like intake / established / HOD / qualification,
#  so these NEVER need to touch the raw file or Gemini.)
# ============================================================

DEPARTMENT_KEYWORDS = {
    "cse": CATEGORY_KEYWORDS["cse"],
    "it": CATEGORY_KEYWORDS["it"],
    "ai": CATEGORY_KEYWORDS["ai"],
    "ece": CATEGORY_KEYWORDS["ece"],
    "eee": CATEGORY_KEYWORDS["eee"],
    "mechanical": CATEGORY_KEYWORDS["mechanical"],
    "civil": CATEGORY_KEYWORDS["civil"],
    "mba": ["mba", "business administration"],
}

DEPARTMENT_FULL_NAMES = {
    "cse": "Computer Science and Engineering",
    "it": "Information Technology",
    "ai": "Artificial Intelligence and Data Science",
    "ece": "Electronics and Communication Engineering",
    "eee": "Electrical and Electronics Engineering",
    "mechanical": "Mechanical Engineering",
    "civil": "Civil Engineering",
}

COURSE_INFO = {
    "civil":      {"name": "B.E. Civil Engineering",                           "established": 2010, "intake": 30},
    "cse":        {"name": "B.E. Computer Science and Engineering",            "established": 2001, "intake": 120},
    "ece":        {"name": "B.E. Electronics and Communication Engineering",   "established": 2001, "intake": 120},
    "eee":        {"name": "B.E. Electrical and Electronics Engineering",      "established": 2001, "intake": 60},
    "mechanical": {"name": "B.E. Mechanical Engineering",                      "established": 2006, "intake": 60},
    "ai":         {"name": "B.Tech. Artificial Intelligence and Data Science", "established": 2023, "intake": 60},
    "it":         {"name": "B.Tech. Information Technology",                   "established": 2024, "intake": 30},
    "mba":        {"name": "M.B.A. Master of Business Administration",         "established": 2026, "intake": 60},
}

# HOD details actually present in the knowledge base. Where the
# knowledge base does not clearly state a qualification or
# specialization for a HOD, it is left as None on purpose - we
# never invent this information (see NOT_FOUND_MESSAGE).
HOD_INFO = {
    "cse": {
        "name": "Dr. S.M. Uma",
        "qualification": "Ph.D.",
        "specialization": "Data Mining",
    },
    "it": {
        "name": "Dr. S.M. Uma",
        "qualification": "Ph.D.",
        "specialization": "Data Mining",
    },
    "ai": {
        "name": "Dr. S.M. Uma",
        "qualification": "Ph.D.",
        "specialization": "Data Mining",
    },
    "ece": {
        "name": "Mrs. N. Mangaiavarkarasi",
        "qualification": "M.E., Ph.D. pursuing",
        "specialization": "Communication Systems",
    },
    "eee": {
        "name": "Mr. R. Sundaramoorthi",
        "qualification": "M.E., Ph.D. pursuing",
        "specialization": "Power Electronics, Electrical Drives, Hybrid Energy",
    },
    "mechanical": {
        "name": "Dr. T. Pushparaj",
        "qualification": "B.E., M.E., Ph.D.",
        "specialization": (
            "Alternative Fuels, Emission Control, Solar Energy, "
            "Heat Exchangers, IC Engines"
        ),
    },
    "civil": {
        "name": "Dr. R. Saravanan",
        "qualification": None,
        "specialization": None,
    },
}

DEPARTMENT_FOCUS = {
    "cse": (
        "programming, data structures, database management, "
        "artificial intelligence, machine learning, cyber security "
        "and cloud computing"
    ),
    "it": (
        "programming, computing, networking, cyber security, "
        "cloud computing and emerging technologies"
    ),
    "ai": (
        "artificial intelligence, data science, machine learning, "
        "deep learning, natural language processing and computer vision"
    ),
    "ece": (
        "signal processing, communication systems, embedded systems, "
        "VLSI and IoT"
    ),
    "eee": (
        "power systems, power electronics, electrical drives "
        "and renewable energy"
    ),
    "mechanical": (
        "thermal engineering, alternative fuels, IC engines "
        "and manufacturing"
    ),
    "civil": (
        "structural engineering, surveying, environmental engineering "
        "and construction technology"
    ),
}


def find_department_key(text):

    if not text:
        return None

    q = normalize_question(text)

    for key, keywords in DEPARTMENT_KEYWORDS.items():

        if any(keyword_matches(q, keyword) for keyword in keywords):
            return key

    return None


def format_department_overview(dept_key):

    course = COURSE_INFO.get(dept_key)

    if not course:
        return None

    lines = [f"**{course['name']}**", ""]

    lines.append(f"• Established: {course['established']}")
    lines.append(f"• Intake: {course['intake']} students")

    hod = HOD_INFO.get(dept_key)
    if hod:
        lines.append(f"• HOD: {hod['name']}")

    focus = DEPARTMENT_FOCUS.get(dept_key)
    if focus:
        lines.append(f"• Focus areas: {focus}")

    return "\n".join(lines)


# ============================================================
# CLEAN COURSES ANSWER (no raw file dump)
# ============================================================

UG_PROGRAMMES = [
    "B.E. Civil Engineering",
    "B.E. Computer Science and Engineering",
    "B.E. Electronics and Communication Engineering",
    "B.E. Electrical and Electronics Engineering",
    "B.E. Mechanical Engineering",
    "B.Tech. Artificial Intelligence and Data Science",
    "B.Tech. Information Technology",
]

PG_PROGRAMMES = [
    "M.E. Computer Science and Engineering",
    "M.E. Power Electronics and Drives",
    "M.E. Thermal Engineering",
    "M.E. VLSI Design",
    "M.B.A. Master of Business Administration",
]

PHD_PROGRAMMES = [
    "Ph.D. Mechanical Engineering",
    "Ph.D. Electronics and Communication Engineering",
]


def format_courses_answer():

    lines = []

    lines.append("KCE offers undergraduate, postgraduate and Ph.D. programmes.")
    lines.append("")

    lines.append("🎓 Undergraduate Programmes")
    for programme in UG_PROGRAMMES:
        lines.append(f"• {programme}")
    lines.append("")

    lines.append("🎓 Postgraduate Programmes")
    for programme in PG_PROGRAMMES:
        lines.append(f"• {programme}")
    lines.append("")

    lines.append("🔬 Ph.D. Programmes")
    for programme in PHD_PROGRAMMES:
        lines.append(f"• {programme}")

    return "\n".join(lines)


# ============================================================
# DIRECT ANSWERS
# ============================================================

def direct_answer(question, previous_question=None):

    q = normalize_question(question)

    # --------------------------------------------------------
    # INTAKE (e.g. "what is the intake for CSE?")
    # Works as a follow-up too: "Tell me about CSE" -> "what is
    # the intake?" (no department named the second time).
    # --------------------------------------------------------

    if "intake" in q:

        dept_key = (
            find_department_key(question)
            or find_department_key(previous_question)
        )

        if dept_key and dept_key in COURSE_INFO:

            info = COURSE_INFO[dept_key]

            return (
                f"The {info['name']} programme has an intake "
                f"of {info['intake']} students."
            )

    # --------------------------------------------------------
    # ESTABLISHED / WHEN STARTED
    # (e.g. "when was IT started?")
    # --------------------------------------------------------

    if any(x in q for x in [
        "when was",
        "established",
        "year of establishment",
        "when did",
        "started",
    ]):

        dept_key = (
            find_department_key(question)
            or find_department_key(previous_question)
        )

        if dept_key and dept_key in COURSE_INFO:

            info = COURSE_INFO[dept_key]

            return (
                f"The {info['name']} programme was "
                f"established in {info['established']}."
            )

    # --------------------------------------------------------
    # QUALIFICATION follow-up (e.g. "what is her qualification?")
    # --------------------------------------------------------

    if "qualification" in q:

        dept_key = (
            find_department_key(question)
            or find_department_key(previous_question)
        )

        if dept_key and dept_key in HOD_INFO:

            info = HOD_INFO[dept_key]

            if info.get("qualification"):

                return (
                    f"{info['name']}, the HOD of "
                    f"{DEPARTMENT_FULL_NAMES[dept_key]}, holds "
                    f"{info['qualification']}."
                )

            return NOT_FOUND_MESSAGE

    # --------------------------------------------------------
    # SPECIALIZATION follow-up (e.g. "what is her specialization?")
    # --------------------------------------------------------

    if "specialization" in q or "specialisation" in q:

        dept_key = (
            find_department_key(question)
            or find_department_key(previous_question)
        )

        if dept_key and dept_key in HOD_INFO:

            info = HOD_INFO[dept_key]

            if info.get("specialization"):

                return (
                    f"{info['name']}'s area of specialization "
                    f"is {info['specialization']}."
                )

            return NOT_FOUND_MESSAGE

    # --------------------------------------------------------
    # HOD (generalized for every department)
    # --------------------------------------------------------

    if "hod" in q or "head of department" in q:

        dept_key = (
            find_department_key(question)
            or find_department_key(previous_question)
        )

        if dept_key and dept_key in HOD_INFO:

            info = HOD_INFO[dept_key]

            return (
                f"The Head of the Department of "
                f"{DEPARTMENT_FULL_NAMES[dept_key]} is {info['name']}."
            )

    # --------------------------------------------------------
    # DEPARTMENT OVERVIEW
    # (e.g. "Tell me about CSE.")
    # --------------------------------------------------------

    about_phrases = [
        "tell me about",
        "about the",
        "information about",
        "details about",
        "overview of",
    ]

    if any(phrase in q for phrase in about_phrases):

        dept_key = find_department_key(question)

        if dept_key:

            overview = format_department_overview(dept_key)

            if overview:
                return overview

    # --------------------------------------------------------
    # COURSES (clean, no raw file dump)
    # --------------------------------------------------------

    course_phrases = [
        "what courses",
        "courses offered",
        "courses are offered",
        "courses available",
        "what programs",
        "what programmes",
        "programs offered",
        "programmes offered",
        "what degree",
        "degrees offered",
        "which courses",
        "which programs",
        "which programmes",
        "what does the college offer",
        "what are the courses",
        "courses in the college",
        "courses in kce",
        "courses at kce",
    ]

    if any(phrase in q for phrase in course_phrases):

        return format_courses_answer()

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if any(x in q for x in [
        "where is the college",
        "where is kce",
        "college location",
        "college located",
        "college address",
        "where is kings college",
        "location of college",
        "location of kce",
        "where is kings college of engineering",
    ]):

        return (
            "Kings College of Engineering is located at:\n\n"
            "Punalkulam, Near Thanjavur,\n"
            "Gandarvakottai Taluk,\n"
            "Pudukkottai District,\n"
            "Tamil Nadu – 613303, India.\n\n"
            "The campus is approximately 10 km from "
            "Thanjavur New Bus Stand on the Pudukkottai Highway."
        )

    # --------------------------------------------------------
    # PRINCIPAL
    # --------------------------------------------------------

    if "principal" in q:

        return (
            "The Principal of Kings College of Engineering is "
            "Dr. J. Arputha Vijaya Selvi, B.E., M.E., Ph.D."
        )

    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------

    if any(x in q for x in [
        "contact number",
        "phone number",
        "college phone",
        "college email",
        "college contact",
        "contact details",
        "contact information",
    ]):

        return (
            "Kings College of Engineering Contact Details:\n\n"
            "📍 Punalkulam, Near Thanjavur, "
            "Gandarvakottai Taluk, Pudukkottai District, "
            "Tamil Nadu – 613303, India.\n\n"
            "📞 Phone: +91-6380989024\n"
            "📧 Email: contact@kingsengg.edu.in\n"
            "🌐 Website: www.kingsengg.edu.in"
        )

    # --------------------------------------------------------
    # LIBRARY
    # --------------------------------------------------------

    if "library" in q:

        return (
            "Yes. Kings College of Engineering has a "
            "fully computerized Central Library.\n\n"
            "The library has more than 33,000 books along with "
            "journals, digital resources, reading facilities, "
            "OPAC, DELNET, NDL, NPTEL and other e-learning resources."
        )

    # --------------------------------------------------------
    # HOSTEL
    # --------------------------------------------------------

    if "hostel" in q:

        return (
            "Kings College of Engineering provides separate "
            "hostels for boys and girls.\n\n"
            "Facilities include furnished rooms, purified water, "
            "mess facilities, study facilities, reading rooms, "
            "recreation facilities, sports, gym facilities "
            "and medical support."
        )

    # --------------------------------------------------------
    # SPORTS
    # --------------------------------------------------------

    if any(x in q for x in [
        "sports",
        "sport facilities",
        "games",
        "playground",
    ]):

        return (
            "Sports facilities at Kings College of Engineering include:\n\n"
            "• Basketball\n"
            "• Volleyball\n"
            "• Tennis\n"
            "• Cricket\n"
            "• Football\n"
            "• Hockey\n"
            "• Badminton\n"
            "• Table Tennis\n"
            "• Kabaddi\n"
            "• Handball\n"
            "• Chess\n"
            "• Carrom\n"
            "• 400 m track\n"
            "• Indoor multi-purpose facilities"
        )

    # --------------------------------------------------------
    # TRANSPORT
    # --------------------------------------------------------

    if any(x in q for x in [
        "transport",
        "college bus",
        "bus facility",
        "bus facilities",
        "bus route",
        "bus routes",
    ]):

        return (
            "Kings College of Engineering provides bus transport "
            "between the college and major towns and surrounding areas.\n\n"
            "Routes include areas such as Thanjavur, Kumbakonam, "
            "Pattukottai, Thiruvaiyaru, Thirukkattupalli, "
            "Ammapet and Gandarvakottai.\n\n"
            "Routes and timings may change, so students should "
            "verify the latest timetable with the college."
        )

    # --------------------------------------------------------
    # PLACEMENT
    # --------------------------------------------------------

    if any(x in q for x in [
        "placement",
        "placements",
        "placement cell",
        "training and placement",
        "recruitment",
    ]):

        return (
            "The Training and Placement Cell supports students through:\n\n"
            "• Campus recruitment\n"
            "• Career guidance\n"
            "• Aptitude training\n"
            "• Technical preparation\n"
            "• Soft-skills training\n"
            "• Industry interaction\n"
            "• Industrial visits\n"
            "• Project guidance\n"
            "• Recruitment drives\n\n"
            "The current Head of Training and Placement is "
            "Prof. Dr. S. Sivakumar."
        )

    # --------------------------------------------------------
    # SCHOLARSHIP
    # --------------------------------------------------------

    if any(x in q for x in [
        "scholarship",
        "scholarships",
        "fee waiver",
        "financial assistance",
    ]):

        return (
            "Scholarship and fee-waiver support mentioned in the "
            "CampusMate knowledge base includes:\n\n"
            "• Government scholarship guidance\n"
            "• Management merit fee waiver\n"
            "• Sports fee waiver\n"
            "• Fee waiver for economically poor students\n"
            "• Sports scholarships\n"
            "• King of Kings Award\n"
            "• Proficiency Award\n"
            "• Best Library User Award\n"
            "• Anna University rank-holder awards\n\n"
            "Eligibility and availability may change, so the latest "
            "details should be verified with the college."
        )

    return None


# ============================================================
# FIND RELEVANT CONTEXT
# ============================================================

def find_relevant_context(question, previous_question=None):

    categories = detect_categories(question, previous_question)

    selected = []

    for category in categories[:3]:

        for number in CATEGORY_SECTIONS.get(
            category,
            []
        ):

            if number not in selected:
                selected.append(number)

    if selected:

        context = get_sections(selected)

        if context:
            return context

    # Keyword fallback

    q = normalize_question(question)

    words = {
        word
        for word in q.split()
        if len(word) >= 3
    }

    scored = []

    for section in KB_SECTIONS:

        text = section["text"].lower()

        score = 0

        for word in words:

            if word in text:
                score += 1

        if score > 0:

            scored.append(
                (score, section)
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return "\n\n".join(
        item[1]["text"]
        for item in scored[:3]
    )


# ============================================================
# GEMINI
# ============================================================

llm = None

if GOOGLE_API_KEY:

    try:

        llm = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2,
            timeout=30,
            max_retries=0,
        )

        print("Gemini configuration: READY")

    except Exception as error:

        print(
            "Gemini initialization error:",
            error
        )

else:

    print(
        "WARNING: GOOGLE_API_KEY not found"
    )


# ============================================================
# ROBUST GEMINI/LANGCHAIN TEXT EXTRACTION
#
# Different versions of Gemini/LangChain can return `.content` as:
#   - a plain string                         -> use it directly
#   - a dict like {"type": "text", "text": ..., "extras": {...}}
#   - a list mixing strings and dicts like the above
#
# This function ONLY ever pulls out the actual "text" - metadata
# keys like "type", "extras", "signature" are always ignored, so
# the user can NEVER see a raw Python object.
# ============================================================

def extract_text_from_gemini_response(content):

    if content is None:
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, dict):
        return str(content.get("text", "")).strip()

    if isinstance(content, list):

        pieces = []

        for item in content:

            if isinstance(item, str):
                pieces.append(item)

            elif isinstance(item, dict):
                text_piece = item.get("text", "")
                if text_piece:
                    pieces.append(str(text_piece))

            # Anything else (unknown object type) is skipped on
            # purpose - we never stringify unknown internal objects.

        return "\n".join(
            piece.strip() for piece in pieces if piece.strip()
        ).strip()

    # Last resort for a type we didn't expect - still try not to
    # leak anything odd-looking; only used if content is, say, a
    # number or something equally harmless.
    return str(content).strip()


# ============================================================
# CLEAN UP RAW KNOWLEDGE-BASE TEXT FOR FALLBACK ANSWERS
# ============================================================

def fallback_answer(context, question=None):

    if not context:
        return NOT_FOUND_MESSAGE

    q = normalize_question(question) if question else ""

    # Only keep raw "Established:" / "Intake:" style lines if the
    # student actually asked about that kind of detail.
    wants_field_detail = any(x in q for x in [
        "established",
        "when was",
        "intake",
        "detail",
        "full list",
        "complete list",
    ])

    lines = []

    for line in context.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("="):
            continue

        # Skip raw numbered section headings, e.g. "5. COURSES OFFERED"
        if re.match(r"^\d+\.\s+[A-Z /&-]+$", line):
            continue

        if "CAMPUSMATE ANSWERING RULES" in line.upper():
            continue

        if not wants_field_detail and re.match(
            r"^(established|intake)\s*:",
            line,
            re.IGNORECASE
        ):
            continue

        lines.append(line)

    if not lines:

        return (
            "I found related information, but I couldn't "
            "prepare a clear answer right now."
        )

    return (
        "Here's what I found in the CampusMate knowledge base:\n\n"
        + "\n".join(lines[:20])
    )


# ============================================================
# BUILD A SHORT CONVERSATION SNIPPET (for follow-up questions)
# ============================================================

def build_conversation_snippet(history, limit=3):

    if not history:
        return "(no previous conversation)"

    recent = history[-(limit * 2):]

    lines = []

    for entry in recent:

        if not isinstance(entry, dict):
            continue

        role = entry.get("role")
        text = str(entry.get("text", "")).strip()

        if not text:
            continue

        if role == "user":
            lines.append(f"Student: {text}")

        elif role == "bot":
            lines.append(f"CampusMate: {text}")

    return "\n".join(lines) if lines else "(no previous conversation)"


def get_previous_user_question(history):

    if not history:
        return None

    for entry in reversed(history):

        if isinstance(entry, dict) and entry.get("role") == "user":
            return str(entry.get("text", "")).strip()

    return None


# ============================================================
# ANSWER A SINGLE QUESTION
# (the core pipeline: direct answer -> knowledge base -> Gemini
#  or fallback. Used directly for normal single questions, and
#  called once per topic when a message has multiple questions.)
# ============================================================

def answer_single_question(question, history, previous_question):

    # ========================================================
    # DIRECT ANSWER FIRST
    # ========================================================

    direct = direct_answer(question, previous_question)

    if direct:
        return direct

    # ========================================================
    # RETRIEVE CONTEXT
    # ========================================================

    context = find_relevant_context(question, previous_question)

    if not context:
        return NOT_FOUND_MESSAGE

    # ========================================================
    # GEMINI UNAVAILABLE
    # ========================================================

    if llm is None:
        return fallback_answer(context, question)

    # ========================================================
    # GEMINI PROMPT
    # ========================================================

    conversation_snippet = build_conversation_snippet(history)

    prompt = f"""
You are CampusMate, the college information assistant
for Kings College of Engineering.

Answer the user's question using ONLY the knowledge base below.

FORMATTING RULES (very important):
- Never show raw section headings like "5. COURSES OFFERED".
- Never show "==================" style dividers.
- Never dump an entire knowledge-base section when only a small
  answer is needed. Answer the exact question that was asked.
- Keep simple questions short and direct (1-3 sentences).
- Give more detail, headings or bullet points ONLY when the
  question needs a list or the student asks for detail.
- When listing items, use clean bullet points ("•"), not raw
  "Established:"/"Intake:" style labels, unless the student
  specifically asked about those details.
- Never invent information that is not in the knowledge base.
- If the information is not available, reply with exactly:
  "{NOT_FOUND_MESSAGE}"
- Do not mention Gemini, AI model, retrieval, context,
  vector database or internal implementation.
- Reply with plain text only - never JSON, never a Python
  dictionary, never any internal object structure.

FOLLOW-UP QUESTIONS:
Use the recent conversation below to understand pronouns or
short follow-up questions (e.g. "her", "his", "it", "the intake").
Only answer using facts that are actually present in the
knowledge base below - never guess.

RECENT CONVERSATION:
{conversation_snippet}

KNOWLEDGE BASE:

{context}

USER QUESTION:

{question}

ANSWER:
"""

    try:

        response = llm.invoke(prompt)

        answer = extract_text_from_gemini_response(
            getattr(response, "content", response)
        )

        if answer:
            return answer

        return fallback_answer(context, question)

    except Exception as error:

        print(
            "GEMINI ERROR:",
            error
        )

        return fallback_answer(context, question)


# ============================================================
# SPLIT A MESSAGE THAT CONTAINS MULTIPLE QUESTIONS
#
# e.g. "Tell me about the library and placements" -> two questions.
#
# Official names that naturally contain "and" (like "Electronics
# and Communication") are protected so they never get cut in half.
# ============================================================

PROTECTED_PHRASES = [
    "artificial intelligence and data science",
    "electronics and communication engineering",
    "electrical and electronics engineering",
    "computer science and engineering",
    "science and humanities",
    "training and placement",
    "research and development",
    "electronics and communication",
    "electrical and electronics",
    "vision and mission",
    "ai and data science",
    "ai and ds",
    "ai & data science",
    "ai & ds",
]


def split_multi_question(question):

    text = question.strip()

    if not text:
        return [text]

    safe_text = text
    placeholder_map = {}

    for index, phrase in enumerate(PROTECTED_PHRASES):

        pattern = re.compile(re.escape(phrase), re.IGNORECASE)

        if pattern.search(safe_text):
            token = f"__PROTECTED_{index}__"
            safe_text = pattern.sub(token, safe_text)
            placeholder_map[token] = phrase

    # Split on common joining words/punctuation used to combine
    # separate questions into one message.
    raw_parts = re.split(
        r"\s*(?:,|;|&|\band\b|\balso\b)\s*",
        safe_text,
        flags=re.IGNORECASE
    )

    parts = []

    for part in raw_parts:

        cleaned = part.strip(" ?.!")

        if not cleaned:
            continue

        for token, phrase in placeholder_map.items():
            cleaned = cleaned.replace(token, phrase)

        parts.append(cleaned)

    # If splitting didn't actually produce more than one piece,
    # just treat the original message as a single question.
    if len(parts) <= 1:
        return [text]

    return parts


def is_meaningful_answer(answer_text):

    if not answer_text:
        return False

    normalized = answer_text.strip().lower()

    if normalized == NOT_FOUND_MESSAGE.lower():
        return False

    return True


def get_label_for_question(text):

    categories = detect_categories(text)

    if not categories:
        return None

    return CATEGORY_LABELS.get(categories[0])


# ============================================================
# MAIN ENTRY POINT (called by the /chat route)
# ============================================================

def ask_gemini(question, history=None):

    history = history if isinstance(history, list) else []

    previous_question = get_previous_user_question(history)

    print("\n" + "=" * 50)
    print("NEW CHAT REQUEST")
    print("USER:", question)
    print("PREVIOUS QUESTION:", previous_question)
    print("=" * 50)

    sub_questions = split_multi_question(question)

    # ------------------------------------------------------
    # Normal case: just one question in the message.
    # ------------------------------------------------------
    if len(sub_questions) <= 1:

        answer = answer_single_question(question, history, previous_question)
        return answer if isinstance(answer, str) else str(answer)

    # ------------------------------------------------------
    # Multiple questions in one message - answer each one and
    # combine them under clear headings.
    # ------------------------------------------------------

    collected = []

    for sub_question in sub_questions:

        answer_text = answer_single_question(
            sub_question, history, previous_question
        )

        if is_meaningful_answer(answer_text):
            label = get_label_for_question(sub_question)
            collected.append((label, answer_text))

    if not collected:
        # Splitting didn't actually help - just answer the
        # original message as a single question.
        answer = answer_single_question(question, history, previous_question)
        return answer if isinstance(answer, str) else str(answer)

    if len(collected) == 1:
        return collected[0][1]

    sections = []

    for label, answer_text in collected:

        if label:
            sections.append(f"{label}\n{answer_text}")
        else:
            sections.append(answer_text)

    return "\n\n".join(sections)


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route("/style.css")
def style():

    return send_from_directory(
        BASE_DIR,
        "style.css"
    )


@app.route("/script.js")
def script():

    return send_from_directory(
        BASE_DIR,
        "script.js"
    )


@app.route("/assets/<path:filename>")
def assets(filename):

    return send_from_directory(
        ASSETS_DIR,
        filename
    )


@app.route("/favicon.ico")
def favicon():

    return "", 204


@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "knowledge_base_loaded": bool(
            KNOWLEDGE_TEXT
        ),
        "sections": len(KB_SECTIONS),
        "gemini_configured": bool(
            GOOGLE_API_KEY
        )
    })


@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        question = str(
            data.get("question", "")
        ).strip()

        history = data.get("history", [])

        if not isinstance(history, list):
            history = []

        if not question:

            return jsonify({
                "answer": "Please enter a question."
            }), 400

        answer = ask_gemini(question, history)

        # Extra safety net: the frontend must ALWAYS receive a
        # plain string, never a dict/list/object of any kind.
        if not isinstance(answer, str):
            answer = extract_text_from_gemini_response(answer)

        if not answer:
            answer = NOT_FOUND_MESSAGE

        return jsonify({
            "answer": answer
        })

    except Exception as error:

        print(
            "CHAT ERROR:",
            error
        )

        return jsonify({
            "answer": (
                "Sorry, something went wrong. "
                "Please try again."
            )
        }), 500


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    debug = (
        os.getenv(
            "FLASK_DEBUG",
            "false"
        ).lower()
        == "true"
    )

    print("\n" + "=" * 60)
    print("CAMPUSMATE SERVER")
    print("=" * 60)
    print("Port:", port)
    print("Debug:", debug)
    print(
        "Knowledge Base:",
        len(KB_SECTIONS),
        "sections"
    )
    print(
        "Gemini Configured:",
        bool(GOOGLE_API_KEY)
    )
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )
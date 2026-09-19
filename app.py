import warnings
warnings.filterwarnings("ignore")

import os
import re

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from langchain_google_genai import ChatGoogleGenerativeAI


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# GOOGLE API KEY
# ============================================================

load_dotenv()

MY_API_KEY = os.getenv("GOOGLE_API_KEY")

print("API KEY LOADED:", bool(MY_API_KEY))

if MY_API_KEY:
    print("API KEY LENGTH:", len(MY_API_KEY))
else:
    print("WARNING: GOOGLE_API_KEY not found.")


# ============================================================
# 1. LOAD COLLEGE KNOWLEDGE BASE
# ============================================================

KNOWLEDGE_FILE = "data/college_info.txt"

try:

    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        college_info = file.read()

    print("Knowledge base loaded successfully.")
    print("Knowledge base characters:", len(college_info))

except Exception as e:

    print("ERROR loading knowledge base:")
    print(e)

    college_info = ""


# ============================================================
# 2. GOOGLE GEMINI
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0.3,
    google_api_key=MY_API_KEY
)


# ============================================================
# 3. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are CampusMate, a student information assistant for
Kings College of Engineering (KCE).

IMPORTANT RULES:

1. Answer ONLY using the supplied KCE knowledge base.

2. Never guess or invent information.

3. If the requested information is not present in the
knowledge base, say exactly:

"I couldn't find that information in the current CampusMate knowledge base."

4. Do not use unrelated information merely because some
words are similar.

5. For department questions, answer using information
belonging to that specific department.

6. For faculty questions, provide faculty information from
the requested department only.

7. For facility questions, list the relevant facilities
instead of giving only a general statement.

8. If the user asks for a list, provide the complete list
available in the knowledge base.

9. If information is historical or year-specific, clearly
mention the year.

10. Keep answers simple, clear and student-friendly.

11. For location or address questions, give the complete
location available in the knowledge base, including
district, state and PIN code when available.

12. Do not answer an unknown question with a greeting.

KCE KNOWLEDGE BASE:

""" + college_info


# ============================================================
# 4. QUERY EXPANSION
# ============================================================

def expand_query(question):

    q = question.lower().strip()


    # --------------------------------------------------------
    # Department abbreviations
    # --------------------------------------------------------

    replacements = {
        "cse": "computer science and engineering",
        "ece": "electronics and communication engineering",
        "eee": "electrical and electronics engineering",
        "mech": "mechanical engineering",
        "civil": "civil engineering",
        "aids": "artificial intelligence and data science",
        "ai&ds": "artificial intelligence and data science",
        "ai ds": "artificial intelligence and data science",
        "it": "information technology",
        "s&h": "science and humanities",
        "s and h": "science and humanities"
    }


    # --------------------------------------------------------
    # Replace complete words
    # --------------------------------------------------------

    for short_name, full_name in replacements.items():

        q = re.sub(
            r'\b' + re.escape(short_name) + r'\b',
            full_name,
            q
        )


    # --------------------------------------------------------
    # Department / Course questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "department",
        "departments",
        "course",
        "courses",
        "program",
        "programs",
        "degree",
        "degrees",
        "offered"
    ]):

        q += """
        courses offered departments academic programs
        undergraduate UG courses
        postgraduate PG courses
        Civil Engineering
        Computer Science and Engineering
        Electronics and Communication Engineering
        Electrical and Electronics Engineering
        Mechanical Engineering
        Artificial Intelligence and Data Science
        Information Technology
        Science and Humanities
        MBA
        M.E
        M.Tech
        B.E
        B.Tech
        """


    # --------------------------------------------------------
    # HOD questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "hod",
        "head of the department",
        "head of department"
    ]):

        q += """
        Head of the Department HOD
        department head
        current HOD
        """


    # --------------------------------------------------------
    # Faculty / Staff questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "faculty",
        "faculties",
        "staff",
        "professor",
        "teachers"
    ]):

        q += """
        faculty members
        teaching staff
        professors
        associate professors
        assistant professors
        department faculty
        """


    # --------------------------------------------------------
    # Hostel questions
    # --------------------------------------------------------

    if "hostel" in q:

        q += """
        boys hostel
        girls hostel
        hostel facilities
        rooms
        mess
        study table
        chair
        shelf
        power
        reading room
        recreation hall
        gym
        sports
        medical dispensary
        purified water
        bathrooms
        """


    # --------------------------------------------------------
    # Library questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "library",
        "books",
        "journal",
        "journals",
        "opac"
    ]):

        q += """
        central library
        library facilities
        books titles volumes
        CD-ROMs
        journals
        magazines
        newspapers
        DELNET
        National Digital Library
        IEEE
        AICTE e-resources
        NPTEL
        OPAC
        reading room
        """


    # --------------------------------------------------------
    # Placement questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "placement",
        "placements",
        "job",
        "recruitment",
        "company",
        "companies"
    ]):

        q += """
        Training and Placement Cell
        campus recruitment
        career guidance
        aptitude training
        technical preparation
        soft skills
        industry interaction
        recruitment drives
        """


    # --------------------------------------------------------
    # Scholarship questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "scholarship",
        "scholarships",
        "fee waiver",
        "award",
        "financial"
    ]):

        q += """
        government scholarship
        management scholarship
        merit based fee waiver
        sports based fee waiver
        economically poor background
        sports scholarship
        King of Kings Award
        Proficiency Award
        Best Library User Award
        Anna University rank holder
        """


    # --------------------------------------------------------
    # Location / Address questions
    # --------------------------------------------------------

    if any(word in q for word in [
        "location",
        "located",
        "where is",
        "where",
        "address",
        "place",
        "situated",
        "campus location",
        "college address",
        "college location"
    ]):

        q += """
        college location
        campus location
        college address
        KCE address
        Kings College of Engineering location
        Kings College of Engineering address
        Punalkulam
        Near Thanjavur
        Gandarvakottai Taluk
        Pudukkottai District
        Tamil Nadu
        613303
        Thanjavur New Bus Stand
        Pudukkottai Highway
        """


    return q


# ============================================================
# 5. CREATE GEMINI QUESTION
# ============================================================

def ask_gemini(user_question):

    expanded_question = expand_query(user_question)

    prompt = f"""
{SYSTEM_PROMPT}

STUDENT QUESTION:

{user_question}

ADDITIONAL SEARCH TERMS:

{expanded_question}

Using ONLY the KCE knowledge base above, answer the student's
question clearly and accurately.
"""

    response = llm.invoke(prompt)

    return response.content


# ============================================================
# 6. CHAT API
# ============================================================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/style.css")
def style():
    return send_from_directory(".", "style.css")


@app.route("/script.js")
def script():
    return send_from_directory(".", "script.js")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory("assets", filename)  

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True)


    if not data:

        return jsonify({
            "answer": "Please ask a valid question."
        }), 400


    user_message = data.get("message", "")


    if not isinstance(user_message, str):

        return jsonify({
            "answer": "Please ask a valid question."
        }), 400


    user_message = user_message.strip()


    if not user_message:

        return jsonify({
            "answer": "Please ask a valid question."
        }), 400


    print("\nUSER QUESTION:")
    print(user_message)


    expanded_question = expand_query(user_message)

    print("\nEXPANDED QUERY:")
    print(expanded_question)


    try:

        answer = ask_gemini(user_message)


        print("\nCAMPUSMATE ANSWER:")
        print(answer)


        return jsonify({
            "answer": answer
        })


    except Exception as e:

        error_message = str(e)

        print("\nCHAT ERROR:")
        print(error_message)


        # ----------------------------------------------------
        # Gemini quota error
        # ----------------------------------------------------

        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
            or "quota" in error_message.lower()
        ):

            return jsonify({
                "answer":
                "⚠️ CampusMate's Gemini API quota has been exhausted. "
                "Please try again later or use another API key."
            }), 429


        # ----------------------------------------------------
        # API key error
        # ----------------------------------------------------

        if (
            "API key" in error_message
            or "API_KEY_INVALID" in error_message
            or "invalid api key" in error_message.lower()
        ):

            return jsonify({
                "answer":
                "⚠️ CampusMate could not connect to Gemini. "
                "Please check the API key configuration."
            }), 500


        # ----------------------------------------------------
        # Other errors
        # ----------------------------------------------------

        return jsonify({
            "answer":
            "Sorry, something went wrong while processing your question."
        }), 500


# ============================================================
# 7. START SERVER
# ============================================================

if __name__ == "__main__":

    print(
        "\n🚀 CampusMate Backend Server Running on "
        "http://127.0.0.1:5000\n"
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
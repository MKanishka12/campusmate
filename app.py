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
# LOAD COLLEGE KNOWLEDGE BASE
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
# GEMINI
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0.3,
    google_api_key=MY_API_KEY
)


# ============================================================
# BASIC QUERY EXPANSION
# ============================================================

def expand_query(question):

    q = question.lower().strip()

    replacements = {
        "cse": "computer science and engineering",
        "ece": "electronics and communication engineering",
        "eee": "electrical and electronics engineering",
        "mech": "mechanical engineering",
        "aids": "artificial intelligence and data science",
        "ai&ds": "artificial intelligence and data science",
        "it": "information technology",
        "s&h": "science and humanities"
    }

    for short_name, full_name in replacements.items():

        q = re.sub(
            r"\b" + re.escape(short_name) + r"\b",
            full_name,
            q
        )

    # Common meaning expansions
    extra_terms = []

    if any(word in q for word in [
        "course",
        "courses",
        "program",
        "programs",
        "degree",
        "degrees",
        "offered"
    ]):
        extra_terms.extend([
            "courses",
            "academic programs",
            "departments",
            "undergraduate",
            "postgraduate",
            "B.E",
            "B.Tech",
            "M.E",
            "M.Tech",
            "MBA"
        ])

    if any(word in q for word in [
        "faculty",
        "faculties",
        "teacher",
        "teachers",
        "professor",
        "staff"
    ]):
        extra_terms.extend([
            "faculty members",
            "teaching staff",
            "professors",
            "associate professors",
            "assistant professors"
        ])

    if "hostel" in q:
        extra_terms.extend([
            "hostel facilities",
            "boys hostel",
            "girls hostel",
            "mess",
            "rooms",
            "reading room",
            "gym"
        ])

    if any(word in q for word in [
        "library",
        "book",
        "books",
        "journal",
        "journals",
        "opac"
    ]):
        extra_terms.extend([
            "central library",
            "library facilities",
            "books",
            "journals",
            "magazines",
            "OPAC",
            "DELNET",
            "NPTEL"
        ])

    if any(word in q for word in [
        "placement",
        "placements",
        "job",
        "recruitment",
        "company",
        "companies"
    ]):
        extra_terms.extend([
            "Training and Placement Cell",
            "campus recruitment",
            "career guidance",
            "aptitude training",
            "technical preparation",
            "soft skills"
        ])

    if any(word in q for word in [
        "scholarship",
        "scholarships",
        "fee waiver",
        "financial"
    ]):
        extra_terms.extend([
            "government scholarship",
            "management scholarship",
            "merit based fee waiver",
            "sports scholarship",
            "financial assistance"
        ])

    if any(word in q for word in [
        "location",
        "located",
        "address",
        "where",
        "situated",
        "place",
        "campus"
    ]):
        extra_terms.extend([
            "college location",
            "college address",
            "campus location",
            "Punalkulam",
            "Thanjavur",
            "Pudukkottai",
            "Tamil Nadu",
            "613303"
        ])

    if extra_terms:
        q += " " + " ".join(extra_terms)

    return q


# ============================================================
# FIND RELEVANT KNOWLEDGE
# ============================================================

def find_relevant_context(question, max_sections=5):

    if not college_info:
        return ""

    expanded_query = expand_query(question)

    # Remove very common words
    stop_words = {
        "the", "is", "are", "was", "were", "what",
        "where", "who", "how", "when", "why",
        "does", "do", "can", "could", "please",
        "tell", "me", "about", "for", "and",
        "or", "of", "to", "in", "on", "a", "an",
        "college", "kce"
    }

    query_words = set(
        word for word in re.findall(
            r"[a-zA-Z0-9&.-]+",
            expanded_query.lower()
        )
        if len(word) > 2 and word not in stop_words
    )

    # Split knowledge base into useful blocks.
    # Blank lines are treated as section boundaries.
    sections = re.split(r"\n\s*\n", college_info)

    scored_sections = []

    for section in sections:

        section_clean = section.strip()

        if not section_clean:
            continue

        section_lower = section_clean.lower()

        score = 0

        for word in query_words:

            if word in section_lower:
                score += 1

                # Give extra weight to exact word repetition
                occurrences = section_lower.count(word)

                if occurrences > 1:
                    score += min(occurrences - 1, 3)

        if score > 0:
            scored_sections.append(
                (score, section_clean)
            )

    # Highest relevance first
    scored_sections.sort(
        key=lambda item: item[0],
        reverse=True
    )

    selected = [
        section
        for score, section in scored_sections[:max_sections]
    ]

    return "\n\n".join(selected)


# ============================================================
# GEMINI RESPONSE NORMALIZER
# ============================================================

def normalize_response(response):

    content = response.content

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):

        text_parts = []

        for item in content:

            if isinstance(item, str):
                text_parts.append(item)

            elif isinstance(item, dict):

                if "text" in item:
                    text_parts.append(str(item["text"]))

                elif "content" in item:
                    text_parts.append(str(item["content"]))

        if text_parts:
            return "\n".join(text_parts).strip()

    if isinstance(content, dict):

        if "text" in content:
            return str(content["text"]).strip()

        if "content" in content:
            return str(content["content"]).strip()

    return str(content).strip()


# ============================================================
# DIRECT KNOWLEDGE BASE FALLBACK
# ============================================================

def direct_knowledge_answer(question):

    context = find_relevant_context(
        question,
        max_sections=3
    )

    if not context:
        return None

    return context


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(user_question):

    relevant_context = find_relevant_context(
        user_question,
        max_sections=5
    )

    if not relevant_context:

        return (
            "I couldn't find that information in the current "
            "CampusMate knowledge base."
        )

    prompt = f"""
You are CampusMate, a student information assistant for
Kings College of Engineering (KCE).

Answer ONLY using the information provided in the
KNOWLEDGE CONTEXT below.

IMPORTANT RULES:

1. Never invent information.

2. Do not use outside knowledge.

3. If the answer is not supported by the context, say exactly:

"I couldn't find that information in the current CampusMate knowledge base."

4. If the user asks for a list, provide all relevant items
available in the supplied context.

5. For department questions, use only the relevant department
information.

6. For faculty questions, provide faculty information from
the relevant department when available.

7. For location questions, provide the complete location
available in the context.

8. Keep the answer simple and student-friendly.

9. Do not mention the internal knowledge base or retrieval
process unless necessary.

KNOWLEDGE CONTEXT:
------------------

{relevant_context}

------------------

STUDENT QUESTION:

{user_question}

Give a clear answer.
"""

    response = llm.invoke(prompt)

    return normalize_response(response)


# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route("/style.css")
def style():

    return send_from_directory(
        ".",
        "style.css"
    )


@app.route("/script.js")
def script():

    return send_from_directory(
        ".",
        "script.js"
    )


@app.route("/assets/<path:filename>")
def assets(filename):

    return send_from_directory(
        "assets",
        filename
    )


# ============================================================
# CHAT API
# ============================================================

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

    print("\n========================================")
    print("USER QUESTION:")
    print(user_message)

    expanded_question = expand_query(user_message)

    print("\nEXPANDED QUERY:")
    print(expanded_question)

    relevant_context = find_relevant_context(
        user_message,
        max_sections=5
    )

    print("\nRELEVANT CONTEXT CHARACTERS:")
    print(len(relevant_context))

    try:

        answer = ask_gemini(user_message)

        print("\nCAMPUSMATE ANSWER:")
        print(answer)

        print("========================================\n")

        return jsonify({
            "answer": answer
        })

    except Exception as e:

        error_message = str(e)

        print("\nCHAT ERROR:")
        print(error_message)

        # ====================================================
        # GEMINI QUOTA EXHAUSTED
        # ====================================================

        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
            or "quota" in error_message.lower()
        ):

            print(
                "Gemini quota exhausted. "
                "Using direct knowledge-base fallback."
            )

            fallback_answer = direct_knowledge_answer(
                user_message
            )

            if fallback_answer:

                return jsonify({
                    "answer":
                    "Gemini is temporarily unavailable, "
                    "so here is the relevant information from "
                    "the CampusMate knowledge base:\n\n"
                    + fallback_answer
                })

            return jsonify({
                "answer":
                "Gemini is temporarily unavailable and "
                "I couldn't find a direct answer in the "
                "CampusMate knowledge base."
            })

        # ====================================================
        # API KEY ERROR
        # ====================================================

        if (
            "API key" in error_message
            or "API_KEY_INVALID" in error_message
            or "invalid api key" in error_message.lower()
        ):

            return jsonify({
                "answer":
                "CampusMate could not connect to Gemini. "
                "Please check the API key configuration."
            }), 500

        # ====================================================
        # OTHER ERROR
        # ====================================================

        print("Unexpected error occurred.")

        return jsonify({
            "answer":
            "Sorry, something went wrong while processing "
            "your question."
        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print(
        "\nCampusMate Backend Server Running on "
        "http://127.0.0.1:5000"
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
import warnings
warnings.filterwarnings("ignore")

import os
import re

from dotenv import load_dotenv

from flask import Flask, request, jsonify
from flask_cors import CORS

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Google Gemini - only for generating answers
from langchain_google_genai import ChatGoogleGenerativeAI

# Local HuggingFace embeddings - no Google embedding quota
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_chroma import Chroma

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# GOOGLE API KEY
# ============================================================

# IMPORTANT:
# Put your own Google AI Studio API key inside the quotes.
# Do NOT share your API key publicly.

load_dotenv()

MY_API_KEY = os.getenv("GOOGLE_API_KEY")


print("API KEY LOADED:", bool(MY_API_KEY))
print("API KEY LENGTH:", len(MY_API_KEY))


# ============================================================
# 1. LOAD KNOWLEDGE BASE
# ============================================================

loader = TextLoader(
    "data/college_info.txt",
    encoding="utf-8"
)

docs = loader.load()

print("Knowledge base loaded successfully.")


# ============================================================
# 2. SPLIT DOCUMENT INTO CHUNKS
# ============================================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200
)

splits = text_splitter.split_documents(docs)

print("Document chunks created:", len(splits))


# ============================================================
# 3. LOCAL HUGGINGFACE EMBEDDINGS
# ============================================================

print("Loading local embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

print("Local embedding model loaded successfully.")


# ============================================================
# 4. CHROMA VECTOR DATABASE
# ============================================================

print("Creating Chroma vector database...")

vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings
)

# Retrieve 8 relevant chunks instead of 6
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 8}
)

print("Chroma vector database ready.")


# ============================================================
# 5. GEMINI LLM
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0.3,
    google_api_key=MY_API_KEY
)


# ============================================================
# 6. SYSTEM PROMPT
# ============================================================

system_prompt = (
    "You are CampusMate, a student information assistant for "
    "Kings College of Engineering (KCE).\n\n"

    "IMPORTANT RULES:\n"

    "1. Answer ONLY from the supplied KCE knowledge base.\n"

    "2. Never guess or invent information.\n"

    "3. Before answering, identify which section of the knowledge base "
    "best matches the student's question.\n"

    "4. Ignore unrelated sections even if they contain similar words.\n"

    "5. For department questions, use the information belonging to that "
    "specific department.\n"

    "6. For faculty questions, provide faculty information from the "
    "requested department only.\n"

    "7. For facility questions, list the relevant facilities instead of "
    "giving only a general statement.\n"

    "8. If the user asks for a list, provide a complete list from the "
    "available context.\n"

    "9. If the requested information is not present in the context, say "
    "'I couldn't find that information in the current CampusMate knowledge base.'\n"

    "10. Do not replace an unknown answer with a greeting.\n"

    "11. Do not answer a question using unrelated information merely because "
    "some words are similar.\n"

    "12. If information is historical or year-specific, clearly mention "
    "the year.\n"

    "13. Keep answers simple, clear and student-friendly.\n"

    "14. For location or address questions, give the complete location "
    "available in the knowledge base, including the district, state and "
    "PIN code when available.\n\n"

    "KCE KNOWLEDGE BASE:\n"
    "{context}"
)


prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])


# ============================================================
# 7. RAG CHAIN
# ============================================================

question_answer_chain = create_stuff_documents_chain(
    llm,
    prompt
)

rag_chain = create_retrieval_chain(
    retriever,
    question_answer_chain
)


# ============================================================
# 8. QUERY EXPANSION
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
    # Replace only complete words
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
# 9. CHAT API
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


    # Expand the question before sending it to the retriever
    expanded_question = expand_query(user_message)

    print("\nUSER QUESTION:")
    print(user_message)

    print("\nEXPANDED QUERY:")
    print(expanded_question)


    try:

        response = rag_chain.invoke({
            "input": expanded_question
        })


        answer = response.get(
            "answer",
            "I couldn't find that information in the current CampusMate knowledge base."
        )


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
        # Other errors
        # ----------------------------------------------------

        return jsonify({
            "answer":
            "Sorry, something went wrong while processing your question."
        }), 500


# ============================================================
# 10. START SERVER
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
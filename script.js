/* ============================================================
   CAMPUSMATE — CHAT ASSISTANT SCRIPT
   Matches: index.html + style.css (premium navy/gold UI)

   Uses RELATIVE backend URLs ("/chat", "/health") so the same
   file works locally (http://127.0.0.1:5000) and on Render,
   with no code changes needed between the two.

   Sends the last few messages of the conversation to the
   backend as "history", so CampusMate can understand short
   follow-up questions (e.g. "what is the intake?" right after
   asking about a department, or "her qualification" right
   after asking about a HOD).

   Also defensive: if the backend ever accidentally sends back
   something that ISN'T a plain string (an object, for example),
   this file will never try to display it directly - it falls
   back to a safe message instead.
   ============================================================ */


/* ---------- ELEMENT REFERENCES ---------- */

const chatMessages    = document.getElementById("chatMessages");
const welcomeScreen   = document.getElementById("welcomeScreen");
const userInput       = document.getElementById("userInput");
const sendButton      = document.getElementById("sendButton");
const clearChatBtn    = document.getElementById("clearChat");
const suggestionsGrid = document.querySelector(".suggestions-grid");
const sidebar         = document.querySelector(".sidebar");
const chatWrapper     = document.querySelector(".chat-wrapper");

let isProcessing = false;

/* RELATIVE endpoints - always point to whichever server is
   currently serving this page (local Flask or Render). */
const CHAT_ENDPOINT   = "/chat";
const HEALTH_ENDPOINT = "/health";

/* Keeps track of the conversation so far, so follow-up
   questions can be understood. Each entry looks like:
   { role: "user" | "bot", text: "..." }
   Only the last few entries are ever sent to the backend. */
const conversationHistory = [];
const MAX_HISTORY_ENTRIES = 20; // last 10 exchanges


/* ---------- WARM UP THE BACKEND ----------
   Render's free plan "sleeps" the server when idle.
   This quiet ping wakes it up early, so the first
   real question replies faster. Errors are ignored
   on purpose — this is not shown to the user. */

fetch(HEALTH_ENDPOINT).catch(() => {});


/* ---------- INSTANT LOCAL RESPONSES ---------- */

const simpleResponses = [
    {
        keywords: ["hi", "hello", "hey"],
        answer: "Hi! 👋 I'm CampusMate. How can I help you with KCE?"
    },
    {
        keywords: ["thank you", "thanks", "thank"],
        answer: "You're welcome! 😊 Feel free to ask me anything about the college."
    },
    {
        keywords: ["bye", "goodbye"],
        answer: "Goodbye! 👋 All the best with your studies. 🎓"
    }
];

function getSimpleResponse(userText) {

    const text = userText.toLowerCase().trim();

    for (const entry of simpleResponses) {
        const match = entry.keywords.some(keyword => text.includes(keyword));
        if (match) {
            return entry.answer;
        }
    }

    return null;
}


/* ---------- SAFE TEXT FORMATTING ---------- */

function escapeHTML(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function formatBotResponse(text) {

    if (!text) {
        return "";
    }

    const safeText = escapeHTML(text);

    return safeText
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/^\s*[\*\-]\s+/gm, "• ")
        .replace(/\n/g, "<br>");
}


/* ---------- ADD A MESSAGE TO THE CHAT ---------- */

function addMessage(text, sender) {

    // Safety net: a bot bubble should NEVER be empty.
    if (!text || !String(text).trim()) {
        text = "Sorry, I couldn't prepare a reply. Please try again.";
    }

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender); // sender: "user" or "bot"

    const bubbleDiv = document.createElement("div");
    bubbleDiv.classList.add("message-bubble");

    if (sender === "bot") {
        bubbleDiv.innerHTML = formatBotResponse(text);
    } else {
        bubbleDiv.textContent = text;
    }

    const timeSpan = document.createElement("span");
    timeSpan.classList.add("message-time");
    timeSpan.textContent = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
    });

    // Time is placed INSIDE the bubble (on its own line) so it
    // works with the existing CSS without needing any CSS changes.
    bubbleDiv.appendChild(timeSpan);

    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);

    scrollToBottom();
}


/* ---------- CONVERSATION HISTORY ---------- */

function rememberInHistory(role, text) {

    conversationHistory.push({ role, text });

    // Keep only the most recent entries so the request stays small.
    while (conversationHistory.length > MAX_HISTORY_ENTRIES) {
        conversationHistory.shift();
    }
}


/* ---------- SCROLL ---------- */

function scrollToBottom() {
    if (chatWrapper) {
        chatWrapper.scrollTop = chatWrapper.scrollHeight;
    }
}


/* ---------- TYPING INDICATOR ---------- */

function showTypingIndicator() {

    const typingWrapper = document.createElement("div");
    typingWrapper.classList.add("message", "bot");
    typingWrapper.id = "typingIndicatorMessage";

    typingWrapper.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

    chatMessages.appendChild(typingWrapper);
    scrollToBottom();
}

function removeTypingIndicator() {
    const typing = document.getElementById("typingIndicatorMessage");
    if (typing) {
        typing.remove();
    }
}


/* ---------- SAFELY READ THE BACKEND'S ANSWER ----------
   The backend is supposed to always send { answer: "some text" }.
   Just in case it ever sends something else by mistake (an
   object, a list, null, a number), this turns it into a safe
   string instead of ever handing a raw object to the UI. */

function extractSafeAnswerText(data) {

    if (!data) {
        return "Sorry, I couldn't find an answer to that question.";
    }

    const answer = data.answer;

    if (typeof answer === "string" && answer.trim()) {
        return answer;
    }

    // Backend accidentally sent something that isn't a plain
    // string (object/array/etc). Never display that directly.
    if (answer !== undefined && answer !== null) {
        console.error("CampusMate: backend returned a non-string answer:", answer);
    }

    return "Sorry, I couldn't prepare a reply. Please try again.";
}


/* ---------- BACKEND REQUEST ---------- */

async function getBotResponse(userText, historyForBackend) {

    const simpleReply = getSimpleResponse(userText);

    if (simpleReply) {
        return simpleReply;
    }

    try {

        const response = await fetch(CHAT_ENDPOINT, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            // IMPORTANT: app.py reads data.get("question", "") and
            // data.get("history", []), so these keys must match.
            body: JSON.stringify({
                question: userText,
                history: historyForBackend
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        return extractSafeAnswerText(data);

    } catch (error) {

        console.error("CampusMate backend error:", error);

        return (
            "Hmm, I couldn't connect to CampusMate right now. " +
            "Please make sure the backend is running."
        );
    }
}


/* ---------- HANDLE A USER MESSAGE ---------- */

async function handleUserMessage(text) {

    const trimmedText = (text || "").trim();

    if (!trimmedText || isProcessing) {
        return;
    }

    isProcessing = true;
    sendButton.disabled = true;

    // Hide the welcome screen (this also hides the suggestion
    // cards, since they live inside the welcome screen).
    if (welcomeScreen) {
        welcomeScreen.style.display = "none";
    }

    // Snapshot the history BEFORE adding this new question, so the
    // backend knows what the "previous" question was.
    const historyForBackend = conversationHistory.slice();

    addMessage(trimmedText, "user");
    rememberInHistory("user", trimmedText);

    userInput.value = "";

    showTypingIndicator();

    const reply = await getBotResponse(trimmedText, historyForBackend);

    removeTypingIndicator();

    addMessage(reply, "bot");
    rememberInHistory("bot", reply);

    sendButton.disabled = false;
    isProcessing = false;
    userInput.focus();
}


/* ---------- SEND BUTTON ---------- */

sendButton.addEventListener("click", () => {
    handleUserMessage(userInput.value);
});


/* ---------- ENTER KEY ---------- */

userInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        event.preventDefault();
        handleUserMessage(userInput.value);
    }
});


/* ---------- SUGGESTION CARDS ---------- */

if (suggestionsGrid) {
    suggestionsGrid.addEventListener("click", event => {

        const card = event.target.closest(".suggestion-card");

        if (!card) {
            return;
        }

        handleUserMessage(card.dataset.question);
    });
}


/* ---------- SIDEBAR QUICK QUESTIONS ---------- */

if (sidebar) {
    sidebar.addEventListener("click", event => {

        const item = event.target.closest(".side-item");

        if (!item || !item.dataset.question) {
            return;
        }

        handleUserMessage(item.dataset.question);
    });
}


/* ---------- CLEAR CHAT ---------- */

clearChatBtn.addEventListener("click", () => {

    chatMessages.innerHTML = "";
    conversationHistory.length = 0; // forget the conversation too

    if (welcomeScreen) {
        welcomeScreen.style.display = "";
    }

    userInput.focus();
});
/* =========================================================
   CAMPUSMATE
   Chat Assistant
========================================================= */

const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const suggestions = document.querySelector(".suggestions-grid");

let isProcessing = false;


/* =========================================================
   SIMPLE LOCAL RESPONSES
========================================================= */

const simpleResponses = [

    {
        keywords: ["hi", "hello", "hey"],
        answer:
            "Hello! 👋 I'm CampusMate. How can I help you explore Kings College of Engineering?"
    },

    {
        keywords: ["thank you", "thanks", "thank"],
        answer:
            "You're welcome! 😊 Feel free to ask me anything about the college."
    },

    {
        keywords: ["bye", "goodbye"],
        answer:
            "Goodbye! 👋 All the best with your studies. 🎓"
    }

];


/* =========================================================
   FORMAT BOT RESPONSE
========================================================= */

function formatBotResponse(text) {

    if (!text) {
        return "";
    }

    const safeText = String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    return safeText

        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")

        .replace(/^\s*[\*\-]\s+/gm, "• ")

        .replace(/\n/g, "<br>");

}


/* =========================================================
   ADD MESSAGE
========================================================= */

function addMessage(text, sender) {

    const messageDiv = document.createElement("div");

    messageDiv.classList.add(
        "message",
        sender === "user"
            ? "user-message"
            : "bot-message"
    );


    const bubbleDiv = document.createElement("div");

    bubbleDiv.classList.add("bubble");


    if (sender === "bot") {

        bubbleDiv.innerHTML =
            formatBotResponse(text);

    } else {

        bubbleDiv.textContent = text;

    }


    const timeDiv = document.createElement("div");

    timeDiv.classList.add("message-time");

    timeDiv.textContent =
        new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        });


    if (sender === "user") {

        messageDiv.appendChild(timeDiv);
        messageDiv.appendChild(bubbleDiv);

    } else {

        messageDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(timeDiv);

    }


    chatWindow.appendChild(messageDiv);

    scrollToBottom();

}


/* =========================================================
   SCROLL
========================================================= */

function scrollToBottom() {

    chatWindow.scrollTop =
        chatWindow.scrollHeight;

}


/* =========================================================
   TYPING INDICATOR
========================================================= */

function showTypingIndicator() {

    const typingDiv =
        document.createElement("div");

    typingDiv.classList.add(
        "message",
        "bot-message"
    );

    typingDiv.id =
        "typing-indicator";


    typingDiv.innerHTML = `

        <div class="bubble typing-bubble">

            <span>CampusMate is typing</span>

            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>

        </div>

    `;


    chatWindow.appendChild(typingDiv);

    scrollToBottom();

}


/* =========================================================
   REMOVE TYPING
========================================================= */

function removeTypingIndicator() {

    const typing =
        document.getElementById(
            "typing-indicator"
        );

    if (typing) {

        typing.remove();

    }

}


/* =========================================================
   SIMPLE RESPONSE CHECK
========================================================= */

function getSimpleResponse(userText) {

    const text =
        userText
            .toLowerCase()
            .trim();


    for (const entry of simpleResponses) {

        const match =
            entry.keywords.some(
                keyword =>
                    text.includes(keyword)
            );


        if (match) {

            return entry.answer;

        }

    }


    return null;

}


/* =========================================================
   BACKEND REQUEST
========================================================= */

async function getBotResponse(userText) {

    const simpleReply =
        getSimpleResponse(userText);


    if (simpleReply) {

        return simpleReply;

    }


    try {

        const response =
            await fetch(
                "http://127.0.0.1:5000/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: userText
                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                `Server returned ${response.status}`
            );

        }


        const data =
            await response.json();


        return (
            data.answer ||
            "Sorry, I couldn't find an answer to that question."
        );

    }


    catch (error) {

        console.error(
            "CampusMate backend error:",
            error
        );


        return (
            "Hmm, I couldn't connect to CampusMate right now. " +
            "Please make sure the Flask backend is running."
        );

    }

}


/* =========================================================
   HANDLE USER MESSAGE
========================================================= */

async function handleUserMessage(text) {

    const trimmedText =
        text.trim();


    if (!trimmedText || isProcessing) {

        return;

    }


    isProcessing = true;

    sendBtn.disabled = true;


    /* Remove welcome screen */

    const welcome =
        document.querySelector(
            ".welcome-screen"
        );


    if (welcome) {

        welcome.remove();

    }


    /* Hide suggestions */

    if (suggestions) {

        suggestions.parentElement.style.display =
            "none";

    }


    /* Add user message */

    addMessage(
        trimmedText,
        "user"
    );


    userInput.value = "";


    /* Typing */

    showTypingIndicator();


    const reply =
        await getBotResponse(
            trimmedText
        );


    removeTypingIndicator();


    /* Bot message */

    addMessage(
        reply,
        "bot"
    );


    sendBtn.disabled = false;

    isProcessing = false;

    userInput.focus();

}


/* =========================================================
   SEND BUTTON
========================================================= */

sendBtn.addEventListener(
    "click",
    () => {

        handleUserMessage(
            userInput.value
        );

    }
);


/* =========================================================
   ENTER KEY
========================================================= */

userInput.addEventListener(
    "keydown",
    event => {

        if (event.key === "Enter") {

            event.preventDefault();

            handleUserMessage(
                userInput.value
            );

        }

    }
);


/* =========================================================
   SUGGESTION CARDS
========================================================= */

if (suggestions) {

    suggestions.addEventListener(
        "click",
        event => {

            const card =
                event.target.closest(
                    ".suggestion-card"
                );


            if (!card) {

                return;

            }


            const question =
                card.dataset.question;


            handleUserMessage(
                question
            );

        }
    );

}


/* =========================================================
   CLEAR CHAT
========================================================= */

clearBtn.addEventListener(
    "click",
    () => {

        chatWindow.innerHTML = `

            <div class="welcome-screen">

                <div class="welcome-logo">

                    <img
                        src="assets/kings.jpeg"
                        alt="Kings College Logo"
                    >

                    <span class="sparkle sparkle-one">✦</span>
                    <span class="sparkle sparkle-two">✦</span>

                </div>

                <div class="welcome-badge">
                    ✨ SMART CAMPUS ASSISTANT
                </div>

                <h2>
                    Hello! I'm
                    <span>CampusMate.</span>
                </h2>

                <p class="welcome-description">

                    Your smart companion for exploring
                    <strong>Kings College of Engineering.</strong>

                    Ask questions and get quick information
                    about the college, departments, facilities
                    and more.

                </p>

                <div class="welcome-features">

                    <div>
                        <span>⚡</span>
                        <p>Quick Answers</p>
                    </div>

                    <div>
                        <span>🎓</span>
                        <p>College Information</p>
                    </div>

                    <div>
                        <span>🔎</span>
                        <p>Smart Search</p>
                    </div>

                </div>

            </div>

        `;


        if (suggestions) {

            suggestions.parentElement.style.display =
                "block";

        }


        userInput.focus();

    }
);


/* =========================================================
   SIDEBAR QUICK QUESTIONS
========================================================= */

function askQuickQuestion(question) {

    handleUserMessage(question);

}
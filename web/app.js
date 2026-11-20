const form = document.getElementById(
    "chat-form"
);

const input = document.getElementById(
    "message-input"
);

const messages = document.getElementById(
    "messages"
);

const sendButton = document.getElementById(
    "send-button"
);

const newChatButton = document.getElementById(
    "new-chat-button"
);

const conversationInfo =
    document.getElementById(
        "conversation-info"
    );

const statusElement =
    document.getElementById(
        "status"
    );

const sourcesPanel =
    document.getElementById(
        "sources-panel"
    );

const sourcesElement =
    document.getElementById(
        "sources"
    );


let conversationId = null;


function addMessage(
    role,
    content,
    isError = false
) {
    const message =
        document.createElement("div");

    message.className =
        `message ${role}`;

    if (isError) {
        message.classList.add("error");
    }

    const label =
        document.createElement("div");

    label.className = "message-label";

    label.textContent =
        role === "user"
            ? "Du"
            : "AI";

    const body =
        document.createElement("div");

    body.className =
        "message-content";

    body.textContent = content;

    message.appendChild(label);
    message.appendChild(body);

    messages.appendChild(message);

    message.scrollIntoView({
        behavior: "smooth",
        block: "end",
    });
}


function showSources(sources) {
    sourcesElement.innerHTML = "";

    if (!sources || sources.length === 0) {
        sourcesPanel.classList.add(
            "hidden"
        );

        return;
    }

    for (const source of sources) {
        const item =
            document.createElement("div");

        item.className = "source";

        const title =
            document.createElement("div");

        title.className =
            "source-title";

        title.textContent =
            source.file_name;

        const metadata =
            document.createElement("div");

        metadata.className =
            "source-meta";

        const location =
            source.page_number === null
                ? `del ${source.chunk_index}`
                : (
                    `side ${source.page_number}, ` +
                    `del ${source.chunk_index}`
                );

        metadata.textContent =
            `${location} · likhet ` +
            `${source.similarity.toFixed(3)}`;

        item.appendChild(title);
        item.appendChild(metadata);

        sourcesElement.appendChild(item);
    }

    sourcesPanel.classList.remove(
        "hidden"
    );
}


function updateConversationInfo() {
    if (!conversationId) {
        conversationInfo.textContent =
            "Ny samtale";

        return;
    }

    conversationInfo.textContent =
        `Conversation ID: ${conversationId}`;
}


async function checkHealth() {
    try {
        const response = await fetch(
            "/health"
        );

        if (!response.ok) {
            throw new Error(
                "API unavailable"
            );
        }

        statusElement.textContent =
            "API tilkoblet";

        statusElement.classList.add(
            "online"
        );

        statusElement.classList.remove(
            "offline"
        );

    } catch {
        statusElement.textContent =
            "API utilgjengelig";

        statusElement.classList.add(
            "offline"
        );

        statusElement.classList.remove(
            "online"
        );
    }
}


async function sendMessage(message) {
    const payload = {
        message: message,
        conversation_id: conversationId,
    };

    const response = await fetch(
        "/chat",
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",
            },

            body: JSON.stringify(payload),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        const detail =
            data.detail
            || "Ukjent API-feil.";

        throw new Error(detail);
    }

    return data;
}


form.addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const message =
            input.value.trim();

        if (!message) {
            return;
        }

        addMessage(
            "user",
            message
        );

        input.value = "";

        sendButton.disabled = true;
        input.disabled = true;

        try {
            const result =
                await sendMessage(
                    message
                );

            conversationId =
                result.conversation_id;

            updateConversationInfo();

            addMessage(
                "assistant",
                result.response
            );

            showSources(
                result.sources
            );

        } catch (error) {
            addMessage(
                "assistant",
                `Feil: ${error.message}`,
                true
            );

        } finally {
            sendButton.disabled = false;
            input.disabled = false;

            input.focus();
        }
    }
);


input.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key === "Enter"
            && !event.shiftKey
        ) {
            event.preventDefault();

            form.requestSubmit();
        }
    }
);


newChatButton.addEventListener(
    "click",
    () => {
        conversationId = null;

        messages.innerHTML = "";

        sourcesElement.innerHTML = "";

        sourcesPanel.classList.add(
            "hidden"
        );

        updateConversationInfo();

        addMessage(
            "assistant",
            "Ny samtale startet. Hva vil du snakke om?"
        );

        input.focus();
    }
);


updateConversationInfo();
checkHealth();
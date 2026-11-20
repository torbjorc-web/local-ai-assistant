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

const conversationList =
    document.getElementById(
        "conversation-list"
    );

const sidebarNewChatButton =
    document.getElementById(
        "sidebar-new-chat-button"
    );

const memoryList =
    document.getElementById(
        "memory-list"
    );

const memoryForm =
    document.getElementById(
        "memory-form"
    );

const memoryInput =
    document.getElementById(
        "memory-input"
    );

const addMemoryButton =
    document.getElementById(
        "add-memory-button"
    );

const memoryStatus =
    document.getElementById(
        "memory-status"
    );

const documentList =
    document.getElementById(
        "document-list"
    );

const indexDocumentsButton =
    document.getElementById(
        "index-documents-button"
    );

const documentStatus =
    document.getElementById(
        "document-status"
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


const documentIndexStatus =
    new Map();


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


async function loadConversations() {
    try {
        const response = await fetch(
            "/conversations"
        );

        if (!response.ok) {
            throw new Error(
                "Kunne ikke hente samtaler."
            );
        }

        const conversations =
            await response.json();

        renderConversations(
            conversations
        );

    } catch (error) {
        conversationList.innerHTML = "";

        const errorElement =
            document.createElement("div");

        errorElement.className =
            "sidebar-placeholder";

        errorElement.textContent =
            error.message;

        conversationList.appendChild(
            errorElement
        );
    }
}


async function loadMemories() {
    try {
        const response = await fetch(
            "/memories"
        );

        if (!response.ok) {
            throw new Error(
                "Kunne ikke hente langtidsminner."
            );
        }

        const memories =
            await response.json();

        renderMemories(memories);

    } catch (error) {
        memoryList.innerHTML = "";

        const errorElement =
            document.createElement("div");

        errorElement.className =
            "sidebar-placeholder";

        errorElement.textContent =
            error.message;

        memoryList.appendChild(
            errorElement
        );
    }
}


async function loadDocuments() {
    try {
        const response = await fetch(
            "/documents"
        );

        if (!response.ok) {
            throw new Error(
                "Kunne ikke hente dokumenter."
            );
        }

        const documents =
            await response.json();

        renderDocuments(documents);

    } catch (error) {
        documentList.innerHTML = "";

        const message =
            document.createElement("div");

        message.className =
            "sidebar-placeholder";

        message.textContent =
            error.message;

        documentList.appendChild(
            message
        );
    }
}


async function indexDocuments() {
    indexDocumentsButton.disabled =
        true;

    documentStatus.textContent =
        "Indekserer dokumenter...";

    documentStatus.className =
        "panel-status";

    try {
        const response = await fetch(
            "/documents/index",
            {
                method: "POST",
            }
        );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail
                || "Indeksering feilet."
            );
        }

        documentIndexStatus.clear();

        let indexedCount = 0;
        let errorCount = 0;

        for (const result of data) {
            documentIndexStatus.set(
                result.file_name,
                result
            );

            if (
                result.status
                === "indexed"
            ) {
                indexedCount += 1;
            } else {
                errorCount += 1;
            }
        }

        if (errorCount === 0) {
            documentStatus.textContent =
                (
                    `${indexedCount} dokumenter ` +
                    "ble indeksert."
                );

            documentStatus.className =
                "panel-status success";
        } else {
            documentStatus.textContent =
                (
                    `${indexedCount} indeksert, ` +
                    `${errorCount} med feil.`
                );

            documentStatus.className =
                "panel-status error";
        }

        await loadDocuments();

    } catch (error) {
        documentStatus.textContent =
            error.message;

        documentStatus.className =
            "panel-status error";

    } finally {
        indexDocumentsButton.disabled =
            false;
    }
}


async function deleteDocument(
    documentId,
    fileName,
    button
) {
    const confirmed = window.confirm(
        (
            `Vil du fjerne "${fileName}" `
            + "fra RAG-indeksen?\n\n"
            + "Originalfilen blir ikke slettet."
        )
    );

    if (!confirmed) {
        return;
    }

    button.disabled = true;

    documentStatus.textContent =
        "Sletter fra indeks...";

    documentStatus.className =
        "panel-status";

    try {
        const response = await fetch(
            `/documents/${documentId}`,
            {
                method: "DELETE",
            }
        );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail
                || "Kunne ikke slette dokumentet."
            );
        }

        documentIndexStatus.delete(
            fileName
        );

        documentStatus.textContent =
            "Dokumentet er fjernet fra RAG-indeksen.";

        documentStatus.className =
            "panel-status success";

        await loadDocuments();

    } catch (error) {
        button.disabled = false;

        documentStatus.textContent =
            error.message;

        documentStatus.className =
            "panel-status error";
    }
}


async function createMemory(content) {
    const response = await fetch(
        "/memories",
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",
            },

            body: JSON.stringify({
                content: content,
                category: "general",
            }),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail
            || "Kunne ikke lagre minnet."
        );
    }

    return data;
}


async function deleteMemory(
    memoryId,
    button
) {
    const confirmed = window.confirm(
        "Vil du slette dette minnet?"
    );

    if (!confirmed) {
        return;
    }

    button.disabled = true;

    memoryStatus.textContent =
        "Sletter...";

    memoryStatus.className =
        "panel-status";

    try {
        const response = await fetch(
            `/memories/${memoryId}`,
            {
                method: "DELETE",
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail
                || "Kunne ikke slette minnet."
            );
        }

        memoryStatus.textContent =
            "Minnet er slettet.";

        memoryStatus.className =
            "panel-status success";

        await loadMemories();

    } catch (error) {
        button.disabled = false;

        memoryStatus.textContent =
            error.message;

        memoryStatus.className =
            "panel-status error";
    }
}


function renderMemories(memories) {
    memoryList.innerHTML = "";

    if (!memories || memories.length === 0) {
        const empty =
            document.createElement("div");

        empty.className =
            "sidebar-placeholder";

        empty.textContent =
            "Ingen langtidsminner lagret.";

        memoryList.appendChild(empty);

        return;
    }

    for (const memory of memories) {
        const item =
            document.createElement("div");

        item.className = "memory-item";

        const category =
            document.createElement("div");

        category.className =
            "memory-category";

        category.textContent =
            memory.category;

        const content =
            document.createElement("div");

        content.className =
            "memory-content";

        content.textContent =
            memory.content;

        const actions =
            document.createElement("div");

        actions.className =
            "memory-actions";

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";

        deleteButton.className =
            "delete-button";

        deleteButton.textContent =
            "Slett";

        deleteButton.addEventListener(
            "click",
            () => {
                deleteMemory(
                    memory.id,
                    deleteButton
                );
            }
        );

        actions.appendChild(
            deleteButton
        );

        item.appendChild(category);
        item.appendChild(content);
        item.appendChild(actions);

        memoryList.appendChild(item);
    }
}


function getDocumentType(fileName) {
    const extension =
        fileName
            .split(".")
            .pop()
            .toLowerCase();

    if (extension === "pdf") {
        return {
            label: "PDF",
            className: "pdf",
        };
    }

    if (extension === "md") {
        return {
            label: "MARKDOWN",
            className: "markdown",
        };
    }

    return {
        label: "TXT",
        className: "text",
    };
}


function renderDocuments(documents) {
    documentList.innerHTML = "";

    if (
        !documents
        || documents.length === 0
    ) {
        const empty =
            document.createElement("div");

        empty.className =
            "sidebar-placeholder";

        empty.textContent =
            "Ingen dokumenter er indeksert.";

        documentList.appendChild(empty);

        return;
    }

    for (const documentEntry of documents) {
        const item =
            document.createElement("div");

        item.className =
            "document-item";

        const header =
            document.createElement("div");

        header.className =
            "document-header";

        const name =
            document.createElement("div");

        name.className =
            "document-name";

        name.textContent =
            documentEntry.file_name;

        header.appendChild(name);

        const meta =
            document.createElement("div");

        meta.className =
            "document-meta";

        const chunkWord =
            documentEntry.chunk_count === 1
                ? "chunk"
                : "chunks";

        meta.textContent =
            `${documentEntry.chunk_count} ${chunkWord}`;

        const badges =
            document.createElement("div");

        badges.className =
            "document-badges";

        const fileType =
            getDocumentType(
                documentEntry.file_name
            );

        const typeBadge =
            document.createElement("span");

        typeBadge.className =
            (
                "document-badge "
                + fileType.className
            );

        typeBadge.textContent =
            fileType.label;

        badges.appendChild(
            typeBadge
        );

        const indexResult =
            documentIndexStatus.get(
                documentEntry.file_name
            );

        if (
            indexResult
            && indexResult.used_ocr
        ) {
            const ocrBadge =
                document.createElement(
                    "span"
                );

            ocrBadge.className =
                "document-badge ocr";

            ocrBadge.textContent =
                "OCR";

            badges.appendChild(
                ocrBadge
            );
        }

        const actions =
            document.createElement("div");

        actions.className =
            "document-actions";

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";

        deleteButton.className =
            "delete-button";

        deleteButton.textContent =
            "Slett fra indeks";

        deleteButton.addEventListener(
            "click",
            () => {
                deleteDocument(
                    documentEntry.id,
                    documentEntry.file_name,
                    deleteButton
                );
            }
        );

        actions.appendChild(
            deleteButton
        );

        item.appendChild(header);
        item.appendChild(meta);
        item.appendChild(badges);
        item.appendChild(actions);

        documentList.appendChild(item);
    }
}


function renderConversations(
    conversations
) {
    conversationList.innerHTML = "";

    if (
        !conversations
        || conversations.length === 0
    ) {
        const empty =
            document.createElement("div");

        empty.className =
            "sidebar-placeholder";

        empty.textContent =
            "Ingen lagrede samtaler.";

        conversationList.appendChild(
            empty
        );

        return;
    }

    for (const conversation of conversations) {
        const button =
            document.createElement("button");

        button.type = "button";

        button.className =
            "conversation-item";

        button.dataset.conversationId =
            conversation.id;

        const title =
            document.createElement("div");

        title.className =
            "conversation-title";

        title.textContent =
            conversation.first_message
            || "Samtale";

        const metadata =
            document.createElement("div");

        metadata.className =
            "conversation-meta";

        metadata.textContent =
            `${conversation.message_count} meldinger`;

        button.appendChild(title);
        button.appendChild(metadata);

        button.addEventListener(
            "click",
            () => {
                loadConversation(
                    conversation.id
                );
            }
        );

        conversationList.appendChild(
            button
        );
    }

    updateActiveConversation();
}


async function loadConversation(
    selectedConversationId
) {
    try {
        const response = await fetch(
            (
                "/conversations/"
                + encodeURIComponent(
                    selectedConversationId
                )
                + "/messages"
            )
        );

        if (!response.ok) {
            throw new Error(
                "Kunne ikke laste samtalen."
            );
        }

        const storedMessages =
            await response.json();

        conversationId =
            selectedConversationId;

        messages.innerHTML = "";

        sourcesElement.innerHTML = "";

        sourcesPanel.classList.add(
            "hidden"
        );

        for (
            const storedMessage
            of storedMessages
        ) {
            if (
                storedMessage.role
                !== "user"
                && storedMessage.role
                !== "assistant"
            ) {
                continue;
            }

            addMessage(
                storedMessage.role,
                storedMessage.content
            );
        }

        updateConversationInfo();

        updateActiveConversation();

        input.focus();

    } catch (error) {
        addMessage(
            "assistant",
            `Feil: ${error.message}`,
            true
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

            await loadConversations();

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


memoryForm.addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const content =
            memoryInput.value.trim();

        if (!content) {
            return;
        }

        addMemoryButton.disabled = true;
        memoryInput.disabled = true;

        memoryStatus.textContent =
            "Lagrer...";

        memoryStatus.className =
            "panel-status";

        try {
            await createMemory(content);

            memoryInput.value = "";

            memoryStatus.textContent =
                "Minnet er lagret.";

            memoryStatus.className =
                "panel-status success";

            await loadMemories();

        } catch (error) {
            memoryStatus.textContent =
                error.message;

            memoryStatus.className =
                "panel-status error";

        } finally {
            addMemoryButton.disabled = false;
            memoryInput.disabled = false;

            memoryInput.focus();
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


function updateActiveConversation() {
    const items =
        conversationList.querySelectorAll(
            ".conversation-item"
        );

    for (const item of items) {
        const isActive =
            item.dataset.conversationId
            === conversationId;

        item.classList.toggle(
            "active",
            isActive
        );
    }
}


function startNewConversation() {
    conversationId = null;

    messages.innerHTML = "";

    sourcesElement.innerHTML = "";

    sourcesPanel.classList.add(
        "hidden"
    );

    updateConversationInfo();

    updateActiveConversation();

    addMessage(
        "assistant",
        "Ny samtale startet. Hva vil du snakke om?"
    );

    input.focus();
}


newChatButton.addEventListener(
    "click",
    startNewConversation
);

sidebarNewChatButton.addEventListener(
    "click",
    startNewConversation
);

indexDocumentsButton.addEventListener(
    "click",
    indexDocuments
);


updateConversationInfo();
checkHealth();
loadConversations();
loadMemories();
loadDocuments();
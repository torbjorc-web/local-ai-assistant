from src.chatbot import Chatbot
from src.config import MODEL


def show_help():
    print("\nTilgjengelige kommandoer:")
    print("  list                  Vis lagrede samtaler")
    print("  load <id>             Last inn en tidligere samtale")
    print("  clear                 Start en ny samtale")
    print("  cleanup               Fjern tomme samtaler")
    print("  remember <tekst>      Lagre et langtidsminne")
    print("  memories              Vis langtidsminner")
    print("  forget <id>           Slett et langtidsminne")
    print("  search-memory <tekst> Søk hybrid i minner")
    print("  reindex-memory        Lag embeddings for gamle minner")
    print("  documents             Vis indekserte dokumenter")
    print("  index-documents       Indekser dokumentmappen")
    print("  search-docs <tekst>   Søk i dokumenter")
    print("  delete-document <id>  Slett dokument fra RAG")
    print("  help                  Vis kommandoene")
    print("  exit                  Avslutt programmet\n")


def show_conversations(chatbot: Chatbot):
    conversations = chatbot.list_conversations()

    if not conversations:
        print("\nIngen lagrede samtaler.\n")
        return

    print("\nLagrede samtaler:")

    for (
        conversation_id,
        created_at,
        message_count,
        first_message,
    ) in conversations:
        preview = first_message.replace("\n", " ").strip()

        if len(preview) > 60:
            preview = preview[:57] + "..."

        active_marker = ""

        if conversation_id == chatbot.conversation_id:
            active_marker = " [aktiv]"

        print(
            f"\nID: {conversation_id}{active_marker}"
            f"\nOpprettet: {created_at}"
            f"\nMeldinger: {message_count}"
            f"\nFørste melding: {preview}"
        )

    print()


def show_memories(chatbot: Chatbot):
    memories = chatbot.list_memories()

    if not memories:
        print("\nIngen langtidsminner lagret.\n")
        return

    print("\nLangtidsminner:")

    for (
        memory_id,
        category,
        content,
        created_at,
    ) in memories:
        print(
            f"\nID: {memory_id}"
            f"\nKategori: {category}"
            f"\nMinne: {content}"
            f"\nOpprettet: {created_at}"
        )

    print()


def show_memory_search_results(results):
    if not results:
        print(
            "\nAI: Fant ingen relevante "
            "indekserte minner.\n"
        )
        return

    print("\nHybride minner:")

    for result in results:
        print(
            f"\nID: {result['id']}"
            f"\nKategori: {result['category']}"
            f"\nSemantisk: {result['semantic_score']:.3f}"
            f"\nNøkkelord: {result['keyword_score']:.3f}"
            f"\nHybrid: {result['hybrid_score']:.3f}"
            f"\nMinne: {result['content']}"
        )

    print()


def show_documents(chatbot: Chatbot):
    documents = chatbot.list_documents()

    if not documents:
        print("\nIngen dokumenter er indeksert.\n")
        return

    print("\nIndekserte dokumenter:")

    for (
        document_id,
        file_name,
        file_path,
        chunk_count,
        updated_at,
        page_count,
        file_size,
        used_ocr,
        extraction_method,
        _,
    ) in documents:
        print(
            f"\nID: {document_id}"
            f"\nFil: {file_name}"
            f"\nChunks: {chunk_count}"
            f"\nSider: {page_count or 'ukjent'}"
            f"\nStørrelse: {file_size} bytes"
            f"\nOCR: {'ja' if used_ocr else 'nei'}"
            f"\nUttrekk: {extraction_method}"
            f"\nOppdatert: {updated_at}"
            f"\nSti: {file_path}"
        )

    print()


def show_document_search_results(results):
    if not results:
        print("\nAI: Fant ingen relevante dokumentutdrag.\n")
        return

    print("\nDokumenttreff:")

    for result in results:
        preview = result["content"].replace(
            "\n",
            " ",
        ).strip()

        if len(preview) > 200:
            preview = preview[:197] + "..."

        page_number = result.get(
            "page_number"
        )

        if page_number is None:
            location = (
                f"Del: {result['chunk_index']}"
            )
        else:
            location = (
                f"Side: {page_number}"
                f"\nDel: {result['chunk_index']}"
            )

        print(
            f"\nFil: {result['file_name']}"
            f"\n{location}"
            f"\nLikhet: {result['similarity']:.3f}"
            f"\nTekst: {preview}"
        )

    print()


def _document_location(document):
    page_number = document.get("page_number")

    if page_number is None:
        return f"del {document['chunk_index']}"

    return (
        f"side {page_number}, "
        f"del {document['chunk_index']}"
    )


def main():
    chatbot = Chatbot()

    print("Local AI Assistant")
    print(f"Model: {MODEL}")
    print("Conversation ID: ingen aktiv samtale")
    print("Skriv 'help' for å vise kommandoene.\n")

    while True:
        user_input = input("Du: ").strip()

        if not user_input:
            continue

        command = user_input.lower()

        # -----------------------------------------------------
        # Exit
        # -----------------------------------------------------

        if command in {"exit", "quit", "avslutt"}:
            print("\nAI: Ha det!")
            break

        # -----------------------------------------------------
        # Help
        # -----------------------------------------------------

        if command == "help":
            show_help()
            continue

        # -----------------------------------------------------
        # List conversations
        # -----------------------------------------------------

        if command == "list":
            show_conversations(chatbot)
            continue

        # -----------------------------------------------------
        # Cleanup empty conversations
        # -----------------------------------------------------

        if command == "cleanup":
            deleted = chatbot.cleanup_empty_conversations()

            if deleted == 0:
                print(
                    "\nAI: Ingen tomme samtaler "
                    "å rydde opp.\n"
                )

            elif deleted == 1:
                print(
                    "\nAI: 1 tom samtale ble slettet.\n"
                )

            else:
                print(
                    f"\nAI: {deleted} tomme samtaler "
                    "ble slettet.\n"
                )

            continue

        # -----------------------------------------------------
        # Start new conversation
        # -----------------------------------------------------

        if command == "clear":
            chatbot.clear_history()

            print("\nAI: Klar for en ny samtale.")
            print(
                "Conversation ID opprettes "
                "ved første melding.\n"
            )

            continue

        # -----------------------------------------------------
        # Load conversation
        # -----------------------------------------------------

        if command == "load":
            print(
                "\nBruk: load <conversation-id>\n"
            )
            continue

        if command.startswith("load "):
            conversation_id = user_input[5:].strip()

            if not conversation_id:
                print(
                    "\nBruk: load <conversation-id>\n"
                )
                continue

            loaded = chatbot.load_conversation(
                conversation_id
            )

            if loaded:
                print(
                    "\nAI: Samtalen er lastet inn."
                )

                print(
                    f"Conversation ID: "
                    f"{chatbot.conversation_id}"
                )

                print(
                    f"Antall tidligere meldinger: "
                    f"{len(chatbot.messages) - 1}\n"
                )

            else:
                print(
                    "\nAI: Fant ingen samtale "
                    "med den ID-en.\n"
                )

            continue

        # -----------------------------------------------------
        # Show long-term memories
        # -----------------------------------------------------

        if command == "memories":
            show_memories(chatbot)
            continue

        # -----------------------------------------------------
        # Remember
        # -----------------------------------------------------

        if command == "remember":
            print(
                "\nBruk: remember <tekst>\n"
            )
            continue

        if command.startswith("remember "):
            content = user_input[9:].strip()

            if not content:
                print(
                    "\nBruk: remember <tekst>\n"
                )
                continue

            try:
                saved = chatbot.remember(content)

                if saved:
                    print(
                        "\nAI: Minnet er lagret "
                        "og indeksert.\n"
                    )
                else:
                    print(
                        "\nAI: Dette minnet "
                        "finnes allerede.\n"
                    )

            except Exception as error:
                print(
                    "\nFeil ved lagring av minne: "
                    f"{error}\n"
                )

            continue

        # -----------------------------------------------------
        # Forget
        # -----------------------------------------------------

        if command == "forget":
            print(
                "\nBruk: forget <memory-id>\n"
            )
            continue

        if command.startswith("forget "):
            memory_id_text = user_input[7:].strip()

            try:
                memory_id = int(memory_id_text)

            except ValueError:
                print(
                    "\nAI: Minne-ID må være et tall.\n"
                )
                continue

            deleted = chatbot.forget(memory_id)

            if deleted:
                print(
                    "\nAI: Minnet er slettet.\n"
                )
            else:
                print(
                    "\nAI: Fant ikke noe minne "
                    "med denne ID-en.\n"
                )

            continue

        # -----------------------------------------------------
        # Reindex old memories
        # -----------------------------------------------------

        if command == "reindex-memory":
            try:
                indexed_count = (
                    chatbot.reindex_memories()
                )

                if indexed_count == 0:
                    print(
                        "\nAI: Alle minner har allerede "
                        "embeddings.\n"
                    )

                elif indexed_count == 1:
                    print(
                        "\nAI: 1 minne ble indeksert.\n"
                    )

                else:
                    print(
                        f"\nAI: {indexed_count} minner "
                        "ble indeksert.\n"
                    )

            except Exception as error:
                print(
                    "\nFeil ved indeksering av minner: "
                    f"{error}\n"
                )

            continue

        # -----------------------------------------------------
        # Hybrid memory search
        # -----------------------------------------------------

        if command == "search-memory":
            print(
                "\nBruk: search-memory <tekst>\n"
            )
            continue

        if command.startswith("search-memory "):
            query = user_input[14:].strip()

            if not query:
                print(
                    "\nBruk: search-memory <tekst>\n"
                )
                continue

            try:
                results = chatbot.search_memories(
                    query
                )

                show_memory_search_results(
                    results
                )

            except Exception as error:
                print(
                    "\nFeil ved hybrid minnesøk: "
                    f"{error}\n"
                )

            continue

        # -----------------------------------------------------
        # Document management
        # -----------------------------------------------------

        if command == "documents":
            show_documents(chatbot)
            continue

        if command == "index-documents":
            try:
                results = chatbot.index_documents()

                if not results:
                    print(
                        "\nAI: Fant ingen støttede dokumenter "
                        "å indeksere.\n"
                    )
                    continue

                print("\nIndeksering ferdig:")

                for result in results:
                    if result["status"] == "indexed":
                        print(
                            f"- {result['file_name']}: "
                            f"{result['chunk_count']} chunks"
                        )
                    else:
                        print(
                            f"- {result['file_name']}: "
                            f"FEIL - {result['error']}"
                        )

                print()

            except Exception as error:
                print(
                    "\nFeil ved dokumentindeksering: "
                    f"{error}\n"
                )

            continue

        if command == "search-docs":
            print("\nBruk: search-docs <tekst>\n")
            continue

        if command.startswith("search-docs "):
            query = user_input[12:].strip()

            if not query:
                print("\nBruk: search-docs <tekst>\n")
                continue

            try:
                results = chatbot.search_documents(query)
                show_document_search_results(results)

            except Exception as error:
                print(
                    "\nFeil ved dokumentsøk: "
                    f"{error}\n"
                )

            continue

        if command == "delete-document":
            print("\nBruk: delete-document <id>\n")
            continue

        if command.startswith("delete-document "):
            document_id_text = user_input[16:].strip()

            try:
                document_id = int(document_id_text)

            except ValueError:
                print("\nAI: Dokument-ID må være et tall.\n")
                continue

            deleted = chatbot.delete_document(document_id)

            if deleted:
                print(
                    "\nAI: Dokumentet og tilhørende "
                    "chunks ble slettet fra RAG-indeksen.\n"
                )
            else:
                print(
                    "\nAI: Fant ikke noe dokument "
                    "med denne ID-en.\n"
                )

            continue

        # -----------------------------------------------------
        # Normal AI message
        # -----------------------------------------------------

        response = chatbot.chat(user_input)

        print(
            f"\nConversation ID: "
            f"{chatbot.conversation_id}"
        )

        print(
            f"\nAI: {response}\n"
        )

        if chatbot.last_document_sources:
            print("Dokumentkilder:")

            shown_sources = set()

            for source in chatbot.last_document_sources:
                source_location = _document_location(
                    source
                )
                source_key = (
                    source["file_name"],
                    source_location,
                )

                if source_key in shown_sources:
                    continue

                shown_sources.add(source_key)

                print(
                    f"- {source['file_name']} "
                    f"({source_location}, "
                    f"likhet {source['similarity']:.3f})"
                )

            print()

if __name__ == "__main__":
    main()
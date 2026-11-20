from src.memory import Memory


def test_tokenize_removes_stopwords():
    memory = Memory()

    tokens = memory._tokenize(
        "Hva vet du om Python og maskinlæring?"
    )

    assert "python" in tokens
    assert "maskinlæring" in tokens
    assert "hva" not in tokens
    assert "du" not in tokens


def test_keyword_similarity_matching_topic():
    memory = Memory()

    score = memory._keyword_similarity(
        "Hvilke spill liker jeg?",
        "Jeg liker Zelda-spillene.",
    )

    assert score > 0


def test_keyword_similarity_unrelated_topic():
    memory = Memory()

    score = memory._keyword_similarity(
        "Hvilke spill liker jeg?",
        "Jeg programmerer i Python.",
    )

    assert score == 0.0
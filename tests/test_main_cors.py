"""Unit tests for _expand_origins in app/main.py — CORS origin expansion logic."""

from app.main import _expand_origins


def test_expand_origins_single_localhost_adds_127_variant() -> None:
    # Arrange
    origins_str = "http://localhost:3000"

    # Act
    result = _expand_origins(origins_str)

    # Assert
    assert "http://localhost:3000" in result
    assert "http://127.0.0.1:3000" in result
    assert len(result) == 2


def test_expand_origins_single_127_adds_localhost_variant() -> None:
    # Arrange
    origins_str = "http://127.0.0.1:5173"

    # Act
    result = _expand_origins(origins_str)

    # Assert
    assert "http://127.0.0.1:5173" in result
    assert "http://localhost:5173" in result
    assert len(result) == 2


def test_expand_origins_multiple_comma_separated() -> None:
    # Arrange
    origins_str = "http://localhost:3000,http://localhost:5173"

    # Act
    result = _expand_origins(origins_str)

    # Assert
    assert "http://localhost:3000" in result
    assert "http://127.0.0.1:3000" in result
    assert "http://localhost:5173" in result
    assert "http://127.0.0.1:5173" in result
    assert len(result) == 4


def test_expand_origins_non_local_origin_passes_through() -> None:
    # Arrange
    origins_str = "https://example.com"

    # Act
    result = _expand_origins(origins_str)

    # Assert
    assert result == ["https://example.com"]


def test_expand_origins_strips_whitespace() -> None:
    # Arrange
    origins_str = "http://localhost:3000 ,  https://example.com"

    # Act
    result = _expand_origins(origins_str)

    # Assert
    assert "http://localhost:3000" in result
    assert "http://127.0.0.1:3000" in result
    assert "https://example.com" in result

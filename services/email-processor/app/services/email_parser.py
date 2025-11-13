"""Email parsing utilities"""
import re
from bs4 import BeautifulSoup
from typing import Dict


def clean_html_to_text(html: str) -> str:
    """
    Convert HTML email to clean plain text

    Args:
        html: HTML content

    Returns:
        Clean plain text
    """
    if not html:
        return ""

    # Parse HTML
    soup = BeautifulSoup(html, "lxml")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())

    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

    # Drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


def extract_best_content(text_body: str, html_body: str) -> str:
    """
    Extract the best content from text or HTML body

    Prefers text body, falls back to HTML converted to text

    Args:
        text_body: Plain text body
        html_body: HTML body

    Returns:
        Clean text content
    """
    if text_body and text_body.strip():
        return text_body.strip()

    if html_body:
        return clean_html_to_text(html_body)

    return ""


def remove_email_noise(text: str) -> str:
    """
    Remove common email noise like signatures, disclaimers, etc.

    Args:
        text: Email text content

    Returns:
        Cleaned text
    """
    # Common signature markers
    signature_markers = [
        r"\n--\s*\n",  # Standard signature delimiter
        r"\nBest regards,",
        r"\nSincerely,",
        r"\nThanks,",
        r"\nRegards,",
        r"\n\-{3,}",  # Multiple dashes
    ]

    # Try to remove everything after signature
    for marker in signature_markers:
        match = re.search(marker, text, re.IGNORECASE)
        if match:
            text = text[:match.start()]
            break

    # Remove unsubscribe footers
    unsubscribe_pattern = r"unsubscribe.*$"
    text = re.sub(unsubscribe_pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def parse_email_content(email_data: Dict) -> Dict:
    """
    Parse and clean email content

    Args:
        email_data: Raw email data from Haraka

    Returns:
        Parsed email data with clean content
    """
    text_body = email_data.get("text", "")
    html_body = email_data.get("html", "")

    # Extract best content
    content = extract_best_content(text_body, html_body)

    # Clean content
    clean_content = remove_email_noise(content)

    return {
        "message_id": email_data.get("message_id", ""),
        "from_address": email_data.get("from_address", ""),
        "to_address": email_data.get("to_addresses", [""])[0] if email_data.get("to_addresses") else "",
        "subject": email_data.get("subject", ""),
        "received_at": email_data.get("received_at", ""),
        "text_body": text_body,
        "html_body": html_body,
        "clean_content": clean_content,
        "headers": email_data.get("headers", {}),
    }

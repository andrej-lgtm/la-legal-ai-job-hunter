"""Candidate profile data model and default candidate configuration for Harrison Wheeler."""

from typing import List
from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    """Structured representation of a candidate's resume and background."""

    name: str = "Harrison Wheeler"
    email: str = "hwheeler11@icloud.com"
    phone: str = "615-934-2968"
    location: str = "Los Angeles, CA"
    target_locations: List[str] = Field(default_factory=lambda: ["Los Angeles, CA", "Los Angeles County"])

    # Education & Bar
    law_school: str = "LMU Loyola Law School"
    degree: str = "Juris Doctor (JD)"
    jd_year: int = 2023
    undergrad: str = "University of Southern California (USC)"
    undergrad_degree: str = "B.A., Philosophy, Politics, and Law, cum laude (2018)"
    bar_state: str = "California"
    bar_year: int = 2023
    years_experience: int = 2  # 2023-Present

    # Legal Tech & AI Superpowers
    certifications: List[str] = Field(
        default_factory=lambda: [
            "Harvey Legal Engineer Certification",
        ]
    )
    ai_skills: List[str] = Field(
        default_factory=lambda: [
            "Harvey",
            "Generative AI",
            "Prompt Engineering",
            "Supervised AI Workflows",
            "Document Review Automation",
            "Model & Vendor Evaluation",
            "LLM Integrations",
            "ChatGPT",
            "Claude (Cowork, Projects, Skills)",
            "Gemini",
            "Codex",
            "Attorney AI Training",
        ]
    )

    # Entertainment & Media Background
    entertainment_employers: List[str] = Field(
        default_factory=lambda: [
            "Metro-Goldwyn-Mayer Studios",
            "MGM",
            "AEG Worldwide",
            "Gaumont International Television",
            "NBCUniversal",
            "Granderson Des Rochers",
            "Loyola of Los Angeles Entertainment Law Review",
        ]
    )
    entertainment_skills: List[str] = Field(
        default_factory=lambda: [
            "Licensing",
            "Distribution",
            "Merchandising",
            "Copyright",
            "Chain-of-Title",
            "Talent Agreements",
            "Sponsorship",
            "Promotional Marketing",
            "IP Clearance",
            "LLC Formations",
        ]
    )

    # Litigation & Corporate Practice
    litigation_skills: List[str] = Field(
        default_factory=lambda: [
            "Civil Litigation",
            "Discovery",
            "Motion Practice",
            "Depositions",
            "Mediation",
            "Settlement Negotiations",
            "Commercial Contracts",
            "Client Counseling",
            "Risk Assessment",
        ]
    )


# Singleton instance for default candidate
HARRISON_WHEELER = CandidateProfile()

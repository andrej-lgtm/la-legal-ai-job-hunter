"""HTML Daily Digest generator."""

from datetime import datetime
from pathlib import Path
from typing import List
from jinja2 import Template
from src.scrapers.base import JobPosting

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Legal & AI Jobs — Los Angeles ({{ date_str }})</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-10 px-4 sm:px-8">
    <div class="max-w-5xl mx-auto">
        <!-- Header -->
        <header class="border-b border-slate-800 pb-8 mb-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <div class="flex items-center gap-2 text-indigo-400 font-semibold tracking-wider text-xs uppercase mb-1">
                        <span>⚖️ Daily Intelligence</span>
                        <span>•</span>
                        <span>Los Angeles & LA Metro</span>
                    </div>
                    <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Legal & AI Job Briefing</h1>
                    <p class="text-slate-400 text-sm mt-1">Targeting In-House Counsel, Associate Counsel, Legal Engineers & Legal AI (JD + 1–3 Years Exp)</p>
                </div>
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 text-right">
                    <div class="text-xs text-slate-400 uppercase font-medium">Briefing Date</div>
                    <div class="text-lg font-bold text-indigo-300">{{ date_str }}</div>
                </div>
            </div>

            <!-- Stats Bar -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
                <div class="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-indigo-400">{{ jobs | length }}</div>
                    <div class="text-xs text-slate-400">Total Matches</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-emerald-400">{{ in_house_count }}</div>
                    <div class="text-xs text-slate-400">In-House Counsel</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-cyan-400">{{ legal_ai_count }}</div>
                    <div class="text-xs text-slate-400">Legal AI & Tech</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-center">
                    <div class="text-2xl font-bold text-amber-400">{{ legal_eng_count }}</div>
                    <div class="text-xs text-slate-400">Legal Engineers</div>
                </div>
            </div>
        </header>

        <!-- Job Cards Section -->
        <main class="space-y-6">
            {% if jobs | length == 0 %}
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                <p class="text-slate-400 text-lg">No qualifying legal jobs found matching today's strict criteria.</p>
                <p class="text-slate-500 text-sm mt-2">The scraper will continue monitoring multiple job boards daily.</p>
            </div>
            {% else %}
                {% for job in jobs %}
                <div class="bg-slate-900 border border-slate-800 hover:border-slate-700 transition rounded-xl p-6 shadow-xl relative overflow-hidden">
                    <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
                        <div class="flex-1">
                            <div class="flex flex-wrap items-center gap-2 mb-2">
                                <!-- Category Badge -->
                                {% if job.category == 'In-House Counsel' %}
                                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">🏢 In-House Counsel</span>
                                {% elif job.category == 'Legal AI' %}
                                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">🤖 Legal & AI</span>
                                {% elif job.category == 'Legal Engineer' %}
                                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">🛠️ Legal Engineer</span>
                                {% else %}
                                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">⚖️ {{ job.category }}</span>
                                {% endif %}

                                <!-- AI Tag if detected -->
                                {% if job.is_legal_ai and job.category != 'Legal AI' %}
                                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">✨ AI / LegalTech</span>
                                {% endif %}

                                <!-- Location Badge -->
                                <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700">
                                    📍 {{ job.location }} {% if job.is_remote %}(Remote){% endif %}
                                </span>
                            </div>

                            <h2 class="text-xl font-bold text-white tracking-tight hover:text-indigo-300 transition">
                                <a href="{{ job.job_url }}" target="_blank" rel="noopener noreferrer">{{ job.title }}</a>
                            </h2>
                            <div class="text-base font-semibold text-slate-300 mt-0.5">
                                {{ job.company }} <span class="text-slate-600 font-normal">•</span> <span class="text-slate-400 font-normal text-xs uppercase">via {{ job.source }}</span>
                            </div>

                            <!-- Snippet -->
                            {% if job.description_snippet %}
                            <p class="text-slate-400 text-sm mt-3 leading-relaxed">
                                {{ job.description_snippet }}
                            </p>
                            {% endif %}

                            <!-- Match Breakdown -->
                            <div class="mt-4 pt-3 border-t border-slate-800/60">
                                <div class="text-xs font-semibold text-slate-500 uppercase mb-1.5 tracking-wider">Criteria Match Breakdown</div>
                                <div class="flex flex-wrap gap-1.5">
                                    {% for reason in job.match_reasons %}
                                    <span class="px-2 py-0.5 rounded bg-slate-950/70 border border-slate-800 text-slate-300 text-xs">{{ reason }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>

                        <!-- Right Column: Match Score & Action -->
                        <div class="flex flex-row md:flex-col items-center md:items-end justify-between gap-3 shrink-0">
                            <!-- Score Circle -->
                            <div class="flex flex-col items-center justify-center w-16 h-16 rounded-2xl bg-indigo-950/80 border border-indigo-500/40 text-center shadow-lg">
                                <span class="text-xl font-black text-indigo-300">{{ job.match_score }}</span>
                                <span class="text-[10px] uppercase font-bold text-indigo-400">Match</span>
                            </div>

                            <a href="{{ job.job_url }}" target="_blank" rel="noopener noreferrer" 
                               class="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-md transition">
                                <span>Apply Now</span>
                                <span>&rarr;</span>
                            </a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% endif %}
        </main>

        <footer class="mt-12 text-center text-xs text-slate-500 border-t border-slate-800/60 pt-6">
            <p>Generated by Legal & AI Job Intelligence Engine • Los Angeles, CA</p>
        </footer>
    </div>
</body>
</html>
"""


def generate_html_digest(jobs: List[JobPosting], output_dir: str = "data/digests") -> Path:
    """Generate a clean standalone HTML daily digest file."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    date_display = datetime.now().strftime("%A, %B %d, %Y")

    in_house_count = sum(1 for j in jobs if j.category == "In-House Counsel")
    legal_ai_count = sum(1 for j in jobs if j.category == "Legal AI" or j.is_legal_ai)
    legal_eng_count = sum(1 for j in jobs if j.category == "Legal Engineer")

    template = Template(HTML_TEMPLATE)
    rendered = template.render(
        jobs=sorted(jobs, key=lambda x: x.match_score, reverse=True),
        date_str=date_display,
        in_house_count=in_house_count,
        legal_ai_count=legal_ai_count,
        legal_eng_count=legal_eng_count,
    )

    file_path = out_path / f"daily_digest_{today_str}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    return file_path

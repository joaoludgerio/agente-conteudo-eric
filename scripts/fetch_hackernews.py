#!/usr/bin/env python3
"""
Coleta top stories do Hacker News relacionadas a IA, tech e produtividade.
Usa a API pública do HN (não precisa de autenticação).
"""

import requests
import json
import sys
from datetime import datetime, timezone

# ============================================
# CONFIGURAÇÃO
# ============================================

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

# Palavras-chave para filtrar stories relevantes ao nicho
KEYWORDS = [
    # IA
    "ai", "artificial intelligence", "llm", "gpt", "claude", "gemini",
    "machine learning", "deep learning", "neural", "openai", "anthropic",
    "chatbot", "copilot", "agent", "agi", "transformer", "diffusion",
    "midjourney", "stable diffusion", "llama", "mistral", "perplexity",
    # Produtividade
    "productivity", "automation", "workflow", "no-code", "low-code",
    "saas", "tool", "app",
    # Tech / Negócios
    "startup", "founder", "entrepreneur", "business", "revenue",
    "funding", "vc", "silicon valley", "tech", "software",
    # Ferramentas específicas
    "notion", "cursor", "replit", "vercel", "supabase", "stripe",
]

# ============================================
# COLETA
# ============================================

def fetch_top_stories(limit=50):
    """Busca os IDs das top stories."""
    try:
        response = requests.get(f"{HN_API_BASE}/topstories.json", timeout=15)
        ids = response.json()
        return ids[:limit]
    except Exception as e:
        print(f"ERRO ao buscar top stories: {e}", file=sys.stderr)
        return []


def fetch_story(story_id):
    """Busca detalhes de uma story específica."""
    try:
        response = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=10)
        return response.json()
    except Exception as e:
        print(f"  ERRO ao buscar story {story_id}: {e}", file=sys.stderr)
        return None


def is_relevant(story):
    """Verifica se a story é relevante para o nicho."""
    if not story or story.get("type") != "story":
        return False

    title = (story.get("title") or "").lower()
    url = (story.get("url") or "").lower()
    text = f"{title} {url}"

    return any(kw in text for kw in KEYWORDS)


def fetch_and_filter(limit=50):
    """Busca top stories e filtra as relevantes."""
    print("Buscando top stories do Hacker News...", file=sys.stderr)
    ids = fetch_top_stories(limit)

    stories = []
    for story_id in ids:
        story = fetch_story(story_id)
        if story and is_relevant(story):
            stories.append({
                "title": story.get("title", ""),
                "url": story.get("url", ""),
                "score": story.get("score", 0),
                "comments": story.get("descendants", 0),
                "by": story.get("by", ""),
                "hn_link": f"https://news.ycombinator.com/item?id={story_id}",
                "time": story.get("time", 0),
            })

    # Ordena por score
    stories.sort(key=lambda x: x["score"], reverse=True)
    print(f"  {len(stories)} stories relevantes encontradas.", file=sys.stderr)
    return stories


def format_for_prompt(stories, max_stories=15):
    """Formata as stories em texto para o prompt."""
    output = []
    output.append("## 🟠 DADOS DO HACKER NEWS (Top stories relevantes)\n")

    if not stories:
        output.append("*Nenhuma story relevante encontrada hoje.*\n")
        return "\n".join(output)

    for i, s in enumerate(stories[:max_stories], 1):
        heat = "🔥🔥🔥" if s["score"] > 500 else "🔥🔥" if s["score"] > 200 else "🔥"

        output.append(f"### {i}. {s['title']}")
        output.append(f"- **Score:** {s['score']} | **Comentários:** {s['comments']} | {heat}")
        output.append(f"- **Link:** {s['url'] or s['hn_link']}")
        output.append(f"- **Discussão HN:** {s['hn_link']}")
        output.append("")

    return "\n".join(output)


# ============================================
# MAIN
# ============================================

def main():
    stories = fetch_and_filter(limit=50)
    output = format_for_prompt(stories)
    print(output)


if __name__ == "__main__":
    main()

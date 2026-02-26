#!/usr/bin/env python3
"""
Coleta posts relevantes do Reddit sobre IA, produtividade e tech.
Usa a API oficial do Reddit com autenticação OAuth2.
"""

import requests
import json
import os
import sys
from datetime import datetime, timezone

# ============================================
# CONFIGURAÇÃO
# ============================================

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USERNAME = os.getenv("REDDIT_USERNAME")
PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = "eric-content-agent/1.0 (by /u/{})".format(USERNAME or "agent")

# Subreddits para monitorar (ajuste conforme necessário)
SUBREDDITS = {
    "artificial": {"category": "IA Geral", "limit": 10},
    "ChatGPT": {"category": "IA Ferramentas", "limit": 8},
    "LocalLLaMA": {"category": "IA Técnico", "limit": 5},
    "singularity": {"category": "IA Futuro", "limit": 5},
    "MachineLearning": {"category": "IA Pesquisa", "limit": 5},
    "Entrepreneur": {"category": "Empreendedorismo", "limit": 5},
    "startups": {"category": "Startups", "limit": 5},
    "productivity": {"category": "Produtividade", "limit": 5},
    "technology": {"category": "Tech Geral", "limit": 5},
    "ArtificialIntelligence": {"category": "IA Negócios", "limit": 5},
    "ClaudeAI": {"category": "IA Ferramentas", "limit": 5},
    "OpenAI": {"category": "IA Ferramentas", "limit": 5},
}

# ============================================
# AUTENTICAÇÃO
# ============================================

def get_access_token():
    """Obtém token OAuth2 do Reddit."""
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }
    headers = {"User-Agent": USER_AGENT}

    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=auth,
        data=data,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:
        print(f"ERRO ao autenticar no Reddit: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return None

    token_data = response.json()
    if "access_token" not in token_data:
        print(f"ERRO: Resposta sem token: {token_data}", file=sys.stderr)
        return None

    return token_data["access_token"]

# ============================================
# COLETA DE POSTS
# ============================================

def fetch_subreddit_top(token, subreddit, limit=10, time_filter="day"):
    """Busca os top posts de um subreddit nas últimas 24h."""
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": USER_AGENT,
    }

    url = f"https://oauth.reddit.com/r/{subreddit}/top"
    params = {"t": time_filter, "limit": limit}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            print(f"  AVISO: r/{subreddit} retornou {response.status_code}", file=sys.stderr)
            return []

        data = response.json()
        posts = []

        for post in data.get("data", {}).get("children", []):
            p = post["data"]
            posts.append({
                "subreddit": subreddit,
                "title": p.get("title", ""),
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "url": p.get("url", ""),
                "permalink": f"https://reddit.com{p.get('permalink', '')}",
                "selftext": (p.get("selftext", "") or "")[:500],  # Primeiros 500 chars
                "created_utc": p.get("created_utc", 0),
                "upvote_ratio": p.get("upvote_ratio", 0),
            })

        return posts

    except Exception as e:
        print(f"  ERRO ao buscar r/{subreddit}: {e}", file=sys.stderr)
        return []


def fetch_all_subreddits(token):
    """Busca posts de todos os subreddits configurados."""
    all_posts = []

    for subreddit, config in SUBREDDITS.items():
        print(f"  Buscando r/{subreddit}...", file=sys.stderr)
        posts = fetch_subreddit_top(token, subreddit, limit=config["limit"])

        for post in posts:
            post["category"] = config["category"]

        all_posts.extend(posts)

    # Ordena por score (mais populares primeiro)
    all_posts.sort(key=lambda x: x["score"], reverse=True)

    return all_posts


def format_for_prompt(posts, max_posts=30):
    """Formata os posts em texto legível para o prompt do Claude."""
    output = []
    output.append("## 📡 DADOS DO REDDIT (Top posts das últimas 24h)\n")

    for i, post in enumerate(posts[:max_posts], 1):
        engagement = post["score"] + (post["num_comments"] * 2)
        heat = "🔥🔥🔥" if engagement > 1000 else "🔥🔥" if engagement > 300 else "🔥"

        output.append(f"### {i}. [{post['category']}] {post['title']}")
        output.append(f"- **Subreddit:** r/{post['subreddit']}")
        output.append(f"- **Score:** {post['score']} | **Comentários:** {post['num_comments']} | **Engajamento:** {heat}")
        output.append(f"- **Link:** {post['permalink']}")

        if post["selftext"]:
            output.append(f"- **Resumo:** {post['selftext'][:300]}...")

        output.append("")

    return "\n".join(output)


# ============================================
# MAIN
# ============================================

def main():
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        print("AVISO: Credenciais do Reddit não configuradas. Pulando coleta do Reddit.", file=sys.stderr)
        print("## 📡 DADOS DO REDDIT\n\n*Credenciais não configuradas. Configure as variáveis de ambiente.*\n")
        return

    print("Autenticando no Reddit...", file=sys.stderr)
    token = get_access_token()

    if not token:
        print("## 📡 DADOS DO REDDIT\n\n*Erro na autenticação. Verifique as credenciais.*\n")
        return

    print("Coletando posts...", file=sys.stderr)
    posts = fetch_all_subreddits(token)

    print(f"Total: {len(posts)} posts coletados.", file=sys.stderr)
    output = format_for_prompt(posts)
    print(output)  # Saída para stdout (capturada pelo script principal)


if __name__ == "__main__":
    main()

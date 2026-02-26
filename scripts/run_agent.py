#!/usr/bin/env python3
"""
Orquestrador do Agente de Conteúdo — Eric Luciano
Coleta dados de múltiplas fontes, monta o prompt e executa o Claude Code.
"""

import subprocess
import os
import sys
from datetime import datetime

# ============================================
# CONFIGURAÇÃO
# ============================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "content-agent.md")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
PAUTAS_FILE = os.path.join(BASE_DIR, "context", "pautas-usadas.md")
TODAY = datetime.now().strftime("%Y-%m-%d")
WEEKDAY = datetime.now().strftime("%A")
REPORT_FILE = os.path.join(REPORTS_DIR, f"{TODAY}.md")

# ============================================
# FUNÇÕES
# ============================================

def run_script(script_name):
    """Executa um script Python e captura o stdout."""
    script_path = os.path.join(BASE_DIR, "scripts", script_name)
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutos max por script
            env=os.environ,
        )
        if result.returncode != 0:
            print(f"AVISO: {script_name} retornou código {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}", file=sys.stderr)
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"AVISO: {script_name} excedeu o timeout.", file=sys.stderr)
        return f"*{script_name} excedeu o tempo limite de execução.*\n"
    except Exception as e:
        print(f"ERRO ao executar {script_name}: {e}", file=sys.stderr)
        return f"*Erro ao executar {script_name}.*\n"


def load_prompt():
    """Carrega e prepara o prompt principal."""
    with open(PROMPT_FILE, "r") as f:
        prompt = f.read()
    return prompt


def load_pautas_usadas():
    """Carrega o histórico de pautas já usadas."""
    try:
        with open(PAUTAS_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def build_full_prompt(reddit_data, hn_data):
    """Monta o prompt completo com todos os dados."""
    prompt_template = load_prompt()
    pautas = load_pautas_usadas()

    # Monta o bloco de dados coletados
    dados_coletados = f"""
---
# 📊 DADOS COLETADOS AUTOMATICAMENTE — {TODAY} ({WEEKDAY})

{reddit_data}

{hn_data}

## 📋 PAUTAS JÁ UTILIZADAS (evite repetir)

{pautas if pautas else "*Nenhuma pauta registrada ainda.*"}

---
"""

    # Substitui placeholders
    full_prompt = prompt_template.replace("{DATA_HOJE}", TODAY)
    full_prompt = full_prompt.replace("{DADOS_COLETADOS}", dados_coletados)

    return full_prompt


def run_claude(prompt):
    """Executa o Claude Code com o prompt."""
    print("Executando Claude Code...", file=sys.stderr)

    try:
        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--allowedTools", "WebSearch",
                "--output-format", "text",
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutos max
            env=os.environ,
        )

        if result.returncode != 0:
            print(f"AVISO: Claude retornou código {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr[:1000]}", file=sys.stderr)

        return result.stdout

    except subprocess.TimeoutExpired:
        print("ERRO: Claude excedeu o timeout de 5 minutos.", file=sys.stderr)
        return "# ⚠️ Erro\n\nO agente excedeu o tempo limite. Tente executar novamente."
    except FileNotFoundError:
        print("ERRO: Claude Code não encontrado. Verifique a instalação.", file=sys.stderr)
        return "# ⚠️ Erro\n\nClaude Code não encontrado no PATH."


def save_report(content):
    """Salva o relatório do dia."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        f.write(content)
    print(f"Relatório salvo: {REPORT_FILE}", file=sys.stderr)


def send_telegram_notification(report_content):
    """Envia notificação para o Telegram (se configurado)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram não configurado. Pulando notificação.", file=sys.stderr)
        return

    import requests as req

    # Extrai as primeiras linhas do relatório como resumo
    lines = report_content.strip().split("\n")
    summary_lines = []
    count = 0
    for line in lines:
        if line.startswith("### ") or line.startswith("## 🔴"):
            summary_lines.append(line.replace("### ", "• ").replace("## ", ""))
            count += 1
            if count >= 8:
                break

    summary = "\n".join(summary_lines) if summary_lines else "Briefing gerado com sucesso!"

    message = f"📰 *Briefing de Conteúdo — {TODAY}*\n\n{summary}\n\n_Confira o relatório completo no GitHub._"

    try:
        req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=15,
        )
        print("Notificação enviada para o Telegram.", file=sys.stderr)
    except Exception as e:
        print(f"AVISO: Erro ao enviar Telegram: {e}", file=sys.stderr)


# ============================================
# MAIN
# ============================================

def main():
    print(f"{'='*50}", file=sys.stderr)
    print(f"Agente de Conteúdo — {TODAY}", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)

    # Passo 1: Coletar dados
    print("\n[1/4] Coletando dados do Reddit...", file=sys.stderr)
    reddit_data = run_script("fetch_reddit.py")

    print("\n[2/4] Coletando dados do Hacker News...", file=sys.stderr)
    hn_data = run_script("fetch_hackernews.py")

    # Passo 2: Montar prompt
    print("\n[3/4] Montando prompt e executando Claude...", file=sys.stderr)
    full_prompt = build_full_prompt(reddit_data, hn_data)

    # Passo 3: Executar Claude
    report = run_claude(full_prompt)

    # Passo 4: Salvar e notificar
    print("\n[4/4] Salvando relatório e notificando...", file=sys.stderr)
    save_report(report)
    send_telegram_notification(report)

    print(f"\n✅ Concluído! Relatório: {REPORT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()

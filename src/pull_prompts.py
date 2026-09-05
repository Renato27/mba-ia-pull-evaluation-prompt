"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import re
import sys
import yaml
from datetime import date
from dotenv import load_dotenv
from langchain import hub
from langsmith import Client
from langchain_core.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

REQUIRED_ENV_VARS = [
    "LANGSMITH_API_KEY",
    "PROMPT_SOURCE_BASE",
    "PROMPT_NAME_BASE",
    "PROMPT_DIR",
]

AUTO_TAGS = {"ChatPromptTemplate", "PromptTemplate", "StructuredPrompt"}


def _block_style_presenter(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _block_style_presenter)


def pull_prompts_from_langsmith(prompt_source: str):
    try:
        return hub.pull(prompt_source)
    except Exception as e:
        print(f"Erro ao fazer pull de {prompt_source}: {e}")
        return None


def fetch_prompt_metadata(prompt_source: str) -> dict:
    try:
        info = Client().get_prompt(prompt_source)
        description = info.description or ""
        tags = [tag for tag in (info.tags or []) if tag not in AUTO_TAGS]
        # info.created_at é um datetime; normaliza para string YYYY-MM-DD, senão
        # o YAML grava uma data nativa em vez de string.
        created_at = (
            info.created_at.date().isoformat() if info.created_at
            else date.today().isoformat()
        )

        if not description:
            print(f"{prompt_source} não tem description no Hub.")
        if not tags:
            print(f"{prompt_source} não tem tags próprias no Hub.")

        return {"description": description, "tags": tags, "created_at": created_at}
    except Exception as e:
        print(f"Não foi possível ler os metadados de {prompt_source}: {e}")
        return {"description": "", "tags": [], "created_at": date.today().isoformat()}


def extract_message_templates(prompt) -> tuple[str, str]:
    system_prompt = ""
    user_prompt = ""

    for message in prompt.messages:
        template = getattr(getattr(message, "prompt", None), "template", None)
        if template is None:
            continue

        if isinstance(message, SystemMessagePromptTemplate):
            system_prompt = template
        elif isinstance(message, HumanMessagePromptTemplate):
            user_prompt = template

    return system_prompt, user_prompt


def build_prompt_data(prompt, prompt_source: str, prompt_name: str) -> dict:
    system_prompt, user_prompt = extract_message_templates(prompt)
    metadata = fetch_prompt_metadata(prompt_source)

    version_match = re.search(r"_(v\d+)$", prompt_name)

    return {
        prompt_name: {
            "description": metadata["description"],
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": version_match.group(1) if version_match else "v1",
            "created_at": metadata["created_at"],
            "tags": metadata["tags"],
        }
    }


def main():
    print_section_header("PULL DO PROMPT DO LANGSMITH HUB")

    if not check_env_vars(REQUIRED_ENV_VARS):
        return 1

    prompt_source = os.getenv("PROMPT_SOURCE_BASE")
    prompt_name = os.getenv("PROMPT_NAME_BASE")
    output_path = f"{os.getenv('PROMPT_DIR')}/{prompt_name}.yml"

    print(f"Fazendo pull de: {prompt_source}")
    prompt = pull_prompts_from_langsmith(prompt_source)
    if prompt is None:
        return 1

    prompt_data = build_prompt_data(prompt, prompt_source, prompt_name)

    system_prompt = prompt_data[prompt_name]["system_prompt"]
    user_prompt = prompt_data[prompt_name]["user_prompt"]
    if not system_prompt and not user_prompt:
        print(f"Nenhum template encontrado em {prompt_source}")
        return 1

    if not save_yaml(prompt_data, output_path):
        return 1

    print(f"Prompt salvo em: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

REQUIRED_FIELDS = ["description", "version", "tags", "user_prompt", "system_prompt"]
REQUIRED_ENV_VARS = ["LANGSMITH_API_KEY", "PROMPT_DIR", "PROMPT_NAME"]


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in prompt_data:
            errors.append(f"Falta o campo obrigatório: {field}")
        elif not prompt_data[field]:
            errors.append(f"Campo obrigatório vazio: {field}")

    system_prompt = prompt_data.get("system_prompt", "")
    user_prompt = prompt_data.get("user_prompt", "")

    if "{bug_report}" not in user_prompt:
        errors.append("O user_prompt precisa conter a variável {bug_report}")

    if "{bug_report}" in system_prompt:
        errors.append(
            "O system_prompt não deve conter {bug_report}: o relato pertence ao "
            "user_prompt (era a duplicação da v1)"
        )

    return len(errors) == 0, errors


def build_prompt_template(prompt_data: dict) -> ChatPromptTemplate:
    """
    Monta o ChatPromptTemplate a partir dos textos do YAML.

    Args:
        prompt_data: Dados do prompt

    Returns:
        ChatPromptTemplate com as mensagens system e human
    """
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("human", prompt_data["user_prompt"]),
    ])


def build_tags(prompt_data: dict) -> list:
    """
    Monta a lista de tags do repositório, incluindo as técnicas aplicadas.

    Args:
        prompt_data: Dados do prompt

    Returns:
        Lista de tags sem duplicatas
    """
    tags = list(prompt_data.get("tags", []))
    tags.append(prompt_data.get("version", ""))

    for technique in prompt_data.get("techniques_applied", []):
        tags.append(technique.lower().replace(" ", "-"))

    # remove vazios e duplicatas preservando a ordem
    return list(dict.fromkeys(tag for tag in tags if tag))


def build_readme(prompt_data: dict) -> str:
    """
    Monta o readme do repositório do prompt no Hub.

    Args:
        prompt_data: Dados do prompt

    Returns:
        Texto em markdown com metadados do prompt
    """
    techniques = prompt_data.get("techniques_applied", [])
    linhas = [
        f"# {prompt_data.get('description', '')}",
        "",
        f"**Versão:** {prompt_data.get('version', '')}",
        f"**Criado em:** {prompt_data.get('created_at', '')}",
        "",
        "## Técnicas de Prompt Engineering aplicadas",
        "",
    ]
    linhas += [f"- {technique}" for technique in techniques]
    linhas += [
        "",
        "## Variáveis de entrada",
        "",
        "- `bug_report`: relato de bug em texto livre",
    ]
    return "\n".join(linhas)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print(f"❌ Erros de validação para o prompt {prompt_name}:")
        for error in errors:
            print(f"   - {error}")
        return False

    try:
        prompt_template = build_prompt_template(prompt_data)
    except Exception as e:
        print(f"❌ Erro ao criar o template do prompt {prompt_name}: {e}")
        return False

    try:
        client = Client()
        url = client.push_prompt(
            prompt_identifier=prompt_name,
            object=prompt_template,
            description=prompt_data.get("description", ""),
            readme=build_readme(prompt_data),
            tags=build_tags(prompt_data),
            is_public=True,
        )
        print(f"✅ Prompt '{prompt_name}' publicado com sucesso.")
        print(f"   URL: {url}")
        return True

    except Exception as e:
        # O Hub recusa um commit idêntico ao último. Não é falha: o conteúdo
        # publicado já é o do YAML local.
        if "has not changed since latest commit" in str(e):
            print(f"✅ Prompt '{prompt_name}' já está publicado nesta versão.")
            print(f"   URL: {Client()._get_prompt_url(prompt_identifier=prompt_name)}")
            return True

        print(f"❌ Erro ao fazer push do prompt {prompt_name}: {e}")

        if "handle" in str(e).lower():
            print(
                "\n   Para publicar um prompt PÚBLICO é preciso criar uma vez o seu\n"
                "   handle do LangChain Hub. Publique qualquer prompt como público em\n"
                "   https://smith.langchain.com/prompts e escolha o username."
            )
        return False


def main():
    """Função principal"""
    print_section_header("PUSH DO PROMPT OTIMIZADO PARA O LANGSMITH HUB")

    if not check_env_vars(REQUIRED_ENV_VARS):
        return 1

    prompt_dir = os.getenv("PROMPT_DIR")
    prompt_name = os.getenv("PROMPT_NAME")

    prompt_file = f"{prompt_dir}/{prompt_name}.yml"
    prompt = load_yaml(prompt_file)
    if prompt is None:
        return 1

    prompt_data = prompt.get(prompt_name)
    if not prompt_data:
        print(f"❌ Chave '{prompt_name}' não encontrada em {prompt_file}")
        return 1

    print(f"📤 Publicando: {prompt_name}")
    if not push_prompt_to_langsmith(prompt_name, prompt_data):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

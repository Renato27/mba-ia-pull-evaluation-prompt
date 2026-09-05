"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    prompts = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in prompts, (
        f"O arquivo {PROMPT_FILE.name} deve ter '{PROMPT_KEY}' como chave raiz"
    )
    return prompts[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' não encontrado"

        system_prompt = prompt_data["system_prompt"]
        assert isinstance(system_prompt, str), "'system_prompt' deve ser uma string"
        assert system_prompt.strip(), "'system_prompt' está vazio"
        assert len(system_prompt) > 200, (
            f"'system_prompt' tem apenas {len(system_prompt)} caracteres; "
            "um prompt otimizado precisa de instruções, regras e exemplos"
        )

    def test_prompt_has_role_definition(self, prompt_data):
        system_prompt = prompt_data.get("system_prompt", "").lower()

        assert "você é" in system_prompt, (
            "O prompt deve definir uma persona explícita começando com 'Você é ...'"
        )

        personas = ["product owner", "product manager", "analista", "engenheiro",
                    "especialista", "product designer"]
        assert any(p in system_prompt for p in personas), (
            f"A persona deve ser um papel reconhecível. Esperado um de: {personas}"
        )

    def test_prompt_mentions_format(self, prompt_data):
        system_prompt = prompt_data.get("system_prompt", "").lower()

        for parte in ["como um", "eu quero", "para que"]:
            assert parte in system_prompt, (
                f"O prompt deve exigir o template de user story; falta '{parte}'"
            )

        assert "critérios de aceitação" in system_prompt, (
            "O prompt deve exigir uma seção de critérios de aceitação"
        )

        for palavra in ["dado que", "quando", "então"]:
            assert palavra in system_prompt, (
                f"Os critérios devem seguir o formato Gherkin; falta '{palavra}'"
            )

    def test_prompt_has_few_shot_examples(self, prompt_data):
        system_prompt = prompt_data.get("system_prompt", "")
        lowered = system_prompt.lower()

        assert "exemplo" in lowered, "O prompt não contém exemplos (Few-shot)"

        n_entradas = lowered.count("entrada:")
        n_saidas = lowered.count("saída:")

        assert n_entradas >= 2, (
            f"Few-shot exige pelo menos 2 exemplos; encontradas {n_entradas} entradas"
        )
        assert n_entradas == n_saidas, (
            f"Cada entrada precisa de uma saída correspondente: "
            f"{n_entradas} entradas e {n_saidas} saídas"
        )

    def test_prompt_no_todos(self, prompt_data):
        marcadores = ["[TODO]", "TODO:", "FIXME", "XXX", "<preencher>", "[preencher]"]

        for campo in ["description", "system_prompt", "user_prompt"]:
            valor = prompt_data.get(campo, "")
            for marcador in marcadores:
                assert marcador not in valor, (
                    f"Marcador '{marcador}' encontrado em '{campo}'"
                )

        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, f"Estrutura inválida: {errors}"

    def test_minimum_techniques(self, prompt_data):
        assert "techniques_applied" in prompt_data, (
            "Metadado 'techniques_applied' não encontrado no YAML"
        )

        tecnicas = prompt_data["techniques_applied"]
        assert isinstance(tecnicas, list), "'techniques_applied' deve ser uma lista"
        assert len(tecnicas) >= 2, (
            f"Mínimo de 2 técnicas requeridas, encontradas: {len(tecnicas)}"
        )
        assert all(isinstance(t, str) and t.strip() for t in tecnicas), (
            "Cada técnica deve ser uma string não vazia"
        )

        assert any("few-shot" in t.lower() for t in tecnicas), (
            f"Few-shot Learning é obrigatória. Técnicas listadas: {tecnicas}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

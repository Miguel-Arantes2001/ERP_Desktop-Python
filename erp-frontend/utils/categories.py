"""Categorias de produto para uma loja agropecuária.

O banco guarda `products.category` como texto. Esta tupla é a fonte
única do que o operador escolhe no cadastro e na edição. O valor
gravado é o próprio nome, então a tabela de estoque continua
exibindo o texto sem tradução.
"""

PRODUCT_CATEGORIES: tuple[str, ...] = (
    "Ração animal",
    "Sal mineral e suplementos",
    "Medicamentos veterinários",
    "Vacinas e biológicos",
    "Higiene animal",
    "Ordenha",
    "Avicultura",
    "Suinocultura",
    "Piscicultura",
    "Equinos e selaria",
    "Pet shop",
    "Sementes",
    "Mudas",
    "Fertilizantes e adubos",
    "Corretivos de solo",
    "Defensivos agrícolas",
    # Inseticida, mosquicida, raticida, formicida, carrapaticida e veneno.
    "Inseticidas e venenos",
    "Ferramentas",
    "Máquinas e equipamentos",
    "Peças e acessórios",
    "Irrigação",
    "Cercas, arames e mourões",
    "Construção rural",
    "Jardinagem",
    "Vestuário e calçados",
    "EPIs",
    "Combustíveis e lubrificantes",
    # Novas categorias entram sempre no fim: renomear ou remover
    # deixaria órfãos os produtos já gravados com o nome antigo.
    "Material veterinário",
    "Pássaros",
    "Animais vivos",
    "Pesca",
    "Ferragens e fixação",
    "Material elétrico",
    "Hidráulica",
    "Tintas e pintura",
    "Soldagem",
    "Utilidades domésticas",
    "Limpeza e piscina",
    "Alimentos e bebidas",
    "Tabacaria",
    "Fogos de artifício",
    "Diversos",
)


def category_options(current: str | None = None) -> tuple[str, ...]:
    """Lista do combo. Inclui a categoria atual se ela não estiver na lista.

    Produtos antigos podem ter sido digitados à mão. Sem este acréscimo,
    abrir a edição perderia o texto que não bate com nenhuma opção.
    """
    current_clean = (current or "").strip()
    if current_clean and current_clean not in PRODUCT_CATEGORIES:
        return (current_clean, *PRODUCT_CATEGORIES)
    return PRODUCT_CATEGORIES

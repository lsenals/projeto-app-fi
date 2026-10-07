"""Paleta e fontes Finapple compartilhadas pelas telas.

Identidade "grafite e dourado discreto" (adotada em 2026-10-07, vinda do canvas de design
"Finapple – Nova Home"): fundo carbono escuro, dourado como único destaque e cinzas
frios para texto. Substitui o verde/amarelo neon da primeira marca (15/09). Os verdes e
vermelhos de lucro/prejuízo continuam semânticos (ft.Colors.GREEN/RED), fora da marca.
Brand book completo no vault do Obsidian (06-Projects).
"""

PRIMARIA = "#C2A15A"      # dourado discreto — destaques, botões, progresso
SECUNDARIA = "#E3C77E"    # dourado claro — recompensas: PRs, XP, ofensiva, metas atingidas
TERCIARIA = "#8FB0BF"     # azul-aço — terceiro anel do Painel de Finanças
FUNDO = "#1A2227"         # carbono — fundo do app
SUPERFICIE = "#222C32"    # carbono, um tom mais claro — cards/superfícies
BORDA = "#2F3B42"         # divisórias e contornos de cards
ICONE_FUNDO = "#2A353C"   # bloco quadrado que abriga um ícone
ICONE_BORDA = "#36434A"
TEXTO = "#E6EAEC"         # texto principal sobre o carbono
TEXTO_TITULO = "#C9D0D3"  # nome da marca e títulos de destaque
TEXTO_SUAVE = "#9AA6AC"   # texto secundário
SETA = "#7D8A90"          # chevron das linhas de navegação
PRATA = "#A9B3B8"         # detalhes do logo

# Fontes empacotadas em src/assets/fonts (OFL; o app não acessa a internet). São fontes
# variáveis: um arquivo cobre todos os pesos. Registradas em main.py via page.fonts.
FONTE_TITULO = "Sora"
FONTE_TEXTO = "Manrope"
FONTES = {
    FONTE_TITULO: "fonts/Sora-Variable.ttf",
    FONTE_TEXTO: "fonts/Manrope-Variable.ttf",
}

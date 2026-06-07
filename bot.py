import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from pathlib import Path

# ── CONFIG ──
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ── DATA ──
def load():
    if not Path(DATA_FILE).exists():
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_char(data, name):
    for k in data:
        if k.lower() == name.lower():
            return data[k]
    return None

def get_key(data, name):
    for k in data:
        if k.lower() == name.lower():
            return k
    return None

# ── EVASIVAS ──
def calcular_evasivas(vel_propria, vel_oponente):
    diff = vel_propria - vel_oponente
    base = 5
    if diff <= 1:
        return base
    elif diff <= 3:
        return base + 2
    elif diff <= 5:
        return base + 4
    else:
        return base + 5

def evasivas_penalidade(vel_propria, vel_oponente):
    diff = vel_oponente - vel_propria
    if diff >= 6:
        return 3
    return 5

# ── REIATSU: CONTROLE, REINO, IMPACTO ──
def calcular_controle_base(reiatsu):
    """Pontos de controle base. A partir de 50k ganham +1, 80k+ ganham +2."""
    if reiatsu >= 80000:
        return 5
    elif reiatsu >= 50000:
        return 4
    else:
        return 3

def analisar_reiatsu(r1, r2, nome1, nome2):
    """Retorna análise completa dos três quesitos de reiatsu."""
    diff = abs(r1 - r2)
    mais_forte = nome1 if r1 >= r2 else nome2
    mais_fraco = nome2 if r1 >= r2 else nome1
    r_forte = max(r1, r2)
    r_fraco = min(r1, r2)

    # CONTROLE
    if diff == 0:
        controle = f"⚖️ **CONTROLE** — Empate total. Ambos gastam 1 ponto por técnica de controle normalmente."
    elif diff < 10000:
        controle = (f"⚖️ **CONTROLE** — Diferença pequena (`{diff:,}`).\n"
                    f"**{mais_forte}** tem leve vantagem: técnicas de controle custam 1pt, resistência leve ao ser controlado.\n"
                    f"**{mais_fraco}** sofre efeitos com ligeiramente mais facilidade.")
    elif diff < 20000:
        controle = (f"🔒 **CONTROLE** — Diferença significativa (`{diff:,}`).\n"
                    f"**{mais_forte}**: técnicas de controle custam 1pt, resistência moderada.\n"
                    f"**{mais_fraco}**: técnicas de controle falham se pontos de controle ≤ 0, maior chance de ser afetado.")
    elif diff < 30000:
        controle = (f"🔒 **CONTROLE** — Diferença alta (`{diff:,}`).\n"
                    f"**{mais_forte}**: controla com facilidade, resistência alta — técnicas do mais fraco exigem +1pt extra para funcionar.\n"
                    f"**{mais_fraco}**: difícil controlar o mais forte. Técnicas custam 1pt extra.")
    else:
        controle = (f"💀 **CONTROLE** — Diferença extrema (`{diff:,}`).\n"
                    f"**{mais_forte}**: controle sem resistência real. Técnicas do mais fraco **automaticamente falham**.\n"
                    f"**{mais_fraco}**: não consegue controlar {mais_forte} independente dos pontos.")

    # REINO / DOMÍNIO
    if diff == 0:
        reino = "⚔️ **CONFLITO DE REINOS** — Confronto real. Nenhum lado tem vantagem de domínio."
    elif diff < 10000:
        reino = (f"⚔️ **CONFLITO DE REINOS** — Pequena vantagem (`{diff:,}`).\n"
                 f"**{mais_forte}** tem leve pressão de domínio, mas o conflito ainda é real.")
    elif diff < 20000:
        reino = (f"🌀 **CONFLITO DE REINOS** — Vantagem alta (`{diff:,}`).\n"
                 f"**{mais_forte}** domina o conflito claramente. Domínio de {mais_fraco} é comprimido.")
    elif diff < 30000:
        reino = (f"🌀 **CONFLITO DE REINOS** — Dominação (`{diff:,}`).\n"
                 f"**{mais_forte}** suprime o domínio de {mais_fraco}. Expansão de reino do mais fraco requer esforço ativo.")
    else:
        reino = (f"👑 **CONFLITO DE REINOS** — Sem conflito (`{diff:,}`).\n"
                 f"**{mais_forte}** expande o domínio **automaticamente**. O reino de {mais_fraco} colapsa sem resistência.")

    # IMPACTO / PRESSÃO
    if diff == 0:
        impacto = "💫 **IMPACTO** — Pressão equivalente. Nenhum efeito de intimidação passiva."
    elif diff < 10000:
        impacto = (f"💫 **IMPACTO** — Pressão leve (`{diff:,}`).\n"
                   f"**{mais_forte}** causa desconforto sutil em {mais_fraco} pela presença.")
    elif diff < 20000:
        impacto = (f"⚡ **IMPACTO** — Pressão real (`{diff:,}`).\n"
                   f"**{mais_forte}**: presença do reiatsu perceptível fisicamente. {mais_fraco} sente dificuldade de concentração.")
    elif diff < 30000:
        impacto = (f"⚡ **IMPACTO** — Pressão severa (`{diff:,}`).\n"
                   f"**{mais_forte}**: reiatsu sufocante. {mais_fraco} pode ter movimento reduzido pela pressão passiva.")
    elif diff < 50000:
        impacto = (f"💀 **IMPACTO** — Pressão esmagadora (`{diff:,}`).\n"
                   f"**{mais_forte}**: aproximar de {mais_fraco} já causa dificuldade de luta. Haki-tipo — paralisar pela presença é possível.")
    else:
        impacto = (f"☠️ **IMPACTO** — Pressão letal (`{diff:,}`).\n"
                   f"**{mais_forte}**: como Helt Coyote com 90k — **{mais_fraco} pode ser incapacitado ou morto apenas pela proximidade.**\n"
                   f"Luta convencional pode ser impossível.")

    return controle, reino, impacto

# ── EMBED DE STATUS ──
def status_embed(name, char):
    estado = char.get("estado", "Base")
    cor = 0x4a7fff if estado == "Base" else 0x30d0c0

    hp_base = char.get("hp_base", char.get("hp_max", char.get("hp", 0)))
    en_base = char.get("energia_base", char.get("energia_max", char.get("energia", 0)))
    hp_max = char.get("hp_max", hp_base)
    en_max = char.get("energia_max", en_base)
    hp = char.get("hp", 0)
    en = char.get("energia", 0)

    hp_pct = int((hp / hp_max * 100)) if hp_max > 0 else 0
    en_pct = int((en / en_max * 100)) if en_max > 0 else 0

    vel = char.get("velocidade", 0)
    evasivas = char.get("evasivas", 5)
    controle = char.get("controle", 3)

    def barra(pct):
        filled = int(pct / 10)
        return "█" * filled + "░" * (10 - filled) + f" {pct}%"

    def barra_evasivas(atual, maximo=10):
        filled = max(0, atual)
        return "◆" * filled + "◇" * (maximo - filled) + f" {atual}"

    def barra_controle(atual):
        filled = max(0, min(5, atual))
        simbolo = "⬛" if atual < 0 else "🟦"
        return "🟦" * filled + "⬜" * (3 - filled) + f" {atual}" if atual >= 0 else f"🔴 {atual} (NEGATIVO)"

    embed = discord.Embed(title=f"◈ {name}", color=cor)
    embed.add_field(name="Estado", value=f"`{estado}`", inline=True)
    embed.add_field(name="Reiatsu", value=f"`{char.get('reiatsu', '—'):,}`", inline=True)
    embed.add_field(name="Velocidade", value=f"`{vel}/10`", inline=True)
    embed.add_field(name=f"HP [{hp:,} / {hp_max:,}]", value=barra(hp_pct), inline=False)
    embed.add_field(name=f"Energia Amaldiçoada [{en:,} / {en_max:,}]", value=barra(en_pct), inline=False)
    embed.add_field(name="LBA", value=f"`{char.get('lba', '—'):,}`", inline=True)
    embed.add_field(name="Evasivas", value=barra_evasivas(evasivas), inline=True)
    embed.add_field(name="Controle", value=barra_controle(controle), inline=True)

    extras = char.get("extras", {})
    if extras:
        for k, v in extras.items():
            embed.add_field(name=k, value=f"`{v}`", inline=True)

    # Estado de transformação
    historico = char.get("historico_transformacoes", [])
    if historico:
        embed.add_field(name="Transformações Ativas", value=" → ".join(historico), inline=False)

    alertas = []
    if hp_pct <= 20:
        alertas.append("⚠️ HP CRÍTICO")
    if en_pct <= 10:
        alertas.append("⚠️ ENERGIA CRÍTICA — IMINENTE INATIVO")
    if en <= 0:
        alertas.append("☠️ ENERGIA ZERADA — PERSONAGEM INATIVO")
    if evasivas == 0:
        alertas.append("💨 SEM EVASIVAS — RECUPERE COM TÉCNICA DE VELOCIDADE")
    if controle <= 0:
        alertas.append(f"🔴 CONTROLE NEGATIVO ({controle}) — TÉCNICAS DE CONTROLE FALHAM")
    if alertas:
        embed.add_field(name="ALERTAS", value="\n".join(alertas), inline=False)

    return embed

# ── SINCRONIZAR ──
@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Bot online: {bot.user} | Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

@tree.command(name="sync", description="[ADMIN] Força sincronização dos comandos neste servidor")
async def sync_cmd(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
        return
    tree.copy_global_to(guild=guild)
    synced = await tree.sync(guild=guild)
    await interaction.response.send_message(
        f"✅ Sincronizados **{len(synced)}** comandos neste servidor.",
        ephemeral=True
    )

# ════════════════════════════════════════════
# PERSONAGENS
# ════════════════════════════════════════════

@tree.command(name="registrar", description="Registra um personagem no sistema")
@app_commands.describe(
    nome="Nome do personagem",
    hp="HP máximo",
    energia="Energia amaldiçoada máxima",
    reiatsu="Reiatsu fixo (10.000 a 100.000)",
    lba="LBA base",
    velocidade="Velocidade de 1 a 10"
)
async def registrar(interaction, nome: str, hp: int, energia: int, reiatsu: int, lba: int, velocidade: app_commands.Range[int, 1, 10]):
    data = load()
    controle_base = calcular_controle_base(reiatsu)
    data[nome] = {
        # Stats atuais
        "hp": hp, "hp_max": hp,
        "energia": energia, "energia_max": energia,
        "reiatsu": reiatsu,
        "lba": lba,
        "velocidade": velocidade,
        "evasivas": 5,
        "controle": controle_base,
        "estado": "Base",
        # Stats base imutáveis (sempre a referência para reverter)
        "hp_base": hp,
        "energia_base": energia,
        "lba_base": lba,
        "velocidade_base": velocidade,
        "controle_base": controle_base,
        # Transformações
        "transformacoes": {},
        "historico_transformacoes": [],
        "extras": {}
    }
    save(data)
    await interaction.response.send_message(
        f"✅ **{nome}** registrado! Controle base: `{controle_base}` (reiatsu `{reiatsu:,}`)",
        embed=status_embed(nome, data[nome])
    )

@tree.command(name="status", description="Mostra o status atual de um personagem")
@app_commands.describe(nome="Nome do personagem")
async def status(interaction, nome: str):
    data = load()
    char = get_char(data, nome)
    if not char:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    await interaction.response.send_message(embed=status_embed(nome, char))

@tree.command(name="todos", description="Mostra o status de todos os personagens")
async def todos(interaction):
    data = load()
    if not data:
        await interaction.response.send_message("Nenhum personagem registrado ainda.")
        return
    await interaction.response.defer()
    for nome, char in data.items():
        await interaction.followup.send(embed=status_embed(nome, char))

@tree.command(name="deletar", description="Remove um personagem do sistema")
@app_commands.describe(nome="Nome do personagem")
async def deletar(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    del data[key]
    save(data)
    await interaction.response.send_message(f"🗑️ **{key}** removido do sistema.")

# ════════════════════════════════════════════
# COMBATE BÁSICO
# ════════════════════════════════════════════

@tree.command(name="dano", description="Aplica dano no HP de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Quantidade de dano")
async def dano(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    antes = char["hp"]
    char["hp"] = max(0, char["hp"] - valor)
    save(data)
    diff = antes - char["hp"]
    await interaction.response.send_message(
        f"💥 **{key}** recebeu `{diff:,}` de dano.\n`HP: {antes:,} → {char['hp']:,}`",
        embed=status_embed(key, char)
    )

@tree.command(name="curar", description="Cura o HP de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Quantidade de cura")
async def curar(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    antes = char["hp"]
    char["hp"] = min(char["hp_max"], char["hp"] + valor)
    save(data)
    diff = char["hp"] - antes
    await interaction.response.send_message(
        f"💚 **{key}** recuperou `{diff:,}` de HP.\n`HP: {antes:,} → {char['hp']:,}`",
        embed=status_embed(key, char)
    )

@tree.command(name="gastar", description="Gasta energia amaldiçoada de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Quantidade de energia gasta")
async def gastar(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    antes = char["energia"]
    char["energia"] = max(0, char["energia"] - valor)
    save(data)
    diff = antes - char["energia"]
    msg = f"⚡ **{key}** gastou `{diff:,}` de energia.\n`Energia: {antes:,} → {char['energia']:,}`"
    if char["energia"] == 0:
        msg += "\n☠️ **ENERGIA ZERADA — PERSONAGEM INATIVO**"
    await interaction.response.send_message(msg, embed=status_embed(key, char))

@tree.command(name="recuperar", description="Recupera energia amaldiçoada de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Quantidade de energia recuperada")
async def recuperar(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    antes = char["energia"]
    char["energia"] = min(char["energia_max"], char["energia"] + valor)
    save(data)
    diff = char["energia"] - antes
    await interaction.response.send_message(
        f"🔵 **{key}** recuperou `{diff:,}` de energia.\n`Energia: {antes:,} → {char['energia']:,}`",
        embed=status_embed(key, char)
    )

@tree.command(name="velocidade", description="Altera a velocidade de um personagem (escala 1-10)")
@app_commands.describe(nome="Nome do personagem", valor="Nova velocidade de 1 a 10")
async def velocidade(interaction, nome: str, valor: app_commands.Range[int, 1, 10]):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    data[key]["velocidade"] = valor
    save(data)
    await interaction.response.send_message(
        f"💨 **{key}** velocidade → `{valor}/10`",
        embed=status_embed(key, data[key])
    )

@tree.command(name="lba", description="Altera o LBA de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Novo valor de LBA")
async def lba(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    data[key]["lba"] = valor
    save(data)
    await interaction.response.send_message(
        f"⚔️ **{key}** LBA → `{valor:,}`",
        embed=status_embed(key, data[key])
    )

# ════════════════════════════════════════════
# EVASIVAS
# ════════════════════════════════════════════

@tree.command(name="evasiva_usar", description="Registra o uso de evasivas em um desvio")
@app_commands.describe(nome="Nome do personagem", quantidade="Quantas evasivas foram gastas")
async def evasiva_usar(interaction, nome: str, quantidade: app_commands.Range[int, 1, 10]):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    antes = char.get("evasivas", 5)
    if antes <= 0:
        await interaction.response.send_message(
            f"❌ **{key}** não tem evasivas restantes. Use `/evasiva_recuperar`.",
            ephemeral=True
        )
        return
    char["evasivas"] = max(0, antes - quantidade)
    save(data)
    msg = f"💨 **{key}** usou `{quantidade}` evasiva(s).\n`Evasivas: {antes} → {char['evasivas']}`"
    if char["evasivas"] == 0:
        msg += "\n💨 **SEM EVASIVAS — RECUPERE COM TÉCNICA DE VELOCIDADE**"
    await interaction.response.send_message(msg, embed=status_embed(key, char))

@tree.command(name="evasiva_recuperar", description="Recupera as evasivas de um personagem (com ou sem comparação de velocidade)")
@app_commands.describe(
    nome="Nome do personagem",
    oponente="(Opcional) Nome do oponente para calcular bônus de velocidade"
)
async def evasiva_recuperar(interaction, nome: str, oponente: str = None):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    v1 = char.get("velocidade", 5)

    if oponente:
        k2 = get_key(data, oponente)
        if not k2:
            await interaction.response.send_message(f"❌ **{oponente}** não encontrado.", ephemeral=True)
            return
        v2 = data[k2].get("velocidade", 5)
        if v1 >= v2:
            novas = calcular_evasivas(v1, v2)
            detalhe = f"Velocidade {v1} vs {v2} → +{novas - 5} bônus" if novas > 5 else f"Velocidade {v1} vs {v2} → sem bônus"
        else:
            novas = evasivas_penalidade(v1, v2)
            detalhe = f"Velocidade {v1} vs {v2} → penalidade (mais lento)"
    else:
        novas = 5
        detalhe = "Recuperação base (sem comparação de velocidade)"

    char["evasivas"] = novas
    save(data)
    await interaction.response.send_message(
        f"💨 **{key}** recuperou evasivas → `{novas}`\n_{detalhe}_",
        embed=status_embed(key, char)
    )

@tree.command(name="comparar_velocidade", description="Mostra a diferença de velocidade e evasivas entre dois personagens")
@app_commands.describe(nome1="Primeiro personagem", nome2="Segundo personagem")
async def comparar_velocidade(interaction, nome1: str, nome2: str):
    data = load()
    k1 = get_key(data, nome1)
    k2 = get_key(data, nome2)
    if not k1 or not k2:
        await interaction.response.send_message("❌ Um dos personagens não foi encontrado.", ephemeral=True)
        return

    v1 = data[k1].get("velocidade", 5)
    v2 = data[k2].get("velocidade", 5)
    diff = abs(v1 - v2)

    ev1 = calcular_evasivas(v1, v2) if v1 >= v2 else evasivas_penalidade(v1, v2)
    ev2 = calcular_evasivas(v2, v1) if v2 >= v1 else evasivas_penalidade(v2, v1)

    embed = discord.Embed(title="💨 COMPARAÇÃO DE VELOCIDADE", color=0x4a7fff)
    embed.add_field(name=k1, value=f"Velocidade: `{v1}/10`\nEvasivas ao recuperar: `{ev1}`", inline=True)
    embed.add_field(name=k2, value=f"Velocidade: `{v2}/10`\nEvasivas ao recuperar: `{ev2}`", inline=True)
    embed.add_field(name="Diferença", value=f"`{diff}` ponto(s)", inline=False)

    if diff == 0:
        embed.add_field(name="Resultado", value="Empate — ambos com 5 evasivas base.", inline=False)
    elif diff <= 1:
        embed.add_field(name="Resultado", value="Empate prático. Sem vantagem real de evasiva.", inline=False)
    elif diff <= 3:
        mais_rapido = k1 if v1 > v2 else k2
        embed.add_field(name="Resultado", value=f"**{mais_rapido}** tem vantagem leve (+2 evasivas).", inline=False)
    elif diff <= 5:
        mais_rapido = k1 if v1 > v2 else k2
        embed.add_field(name="Resultado", value=f"**{mais_rapido}** tem vantagem clara (+4 evasivas).", inline=False)
    else:
        mais_rapido = k1 if v1 > v2 else k2
        mais_lento = k2 if v1 > v2 else k1
        embed.add_field(name="Resultado", value=f"**{mais_rapido}** domina em velocidade (+5 evasivas). **{mais_lento}** cai para 3 evasivas.", inline=False)

    await interaction.response.send_message(embed=embed)

# ════════════════════════════════════════════
# TRANSFORMAÇÕES — SISTEMA CORRIGIDO
# ════════════════════════════════════════════

@tree.command(name="registrar_transformacao", description="Registra uma transformação para um personagem")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação (ex: Shikai, Bankai, Ressurreição)",
    hp_mult="Multiplicador de HP (ex: 1.5). Use 1 pra não mudar.",
    energia_mult="Multiplicador de Energia. Use 1 pra não mudar.",
    lba_mult="Multiplicador de LBA. Use 1 pra não mudar.",
    vel_add="Pontos de velocidade a adicionar (ex: 1). Use 0 pra não mudar."
)
async def registrar_transformacao(interaction, nome: str, estado: str, hp_mult: float, energia_mult: float, lba_mult: float, vel_add: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    if "transformacoes" not in data[key]:
        data[key]["transformacoes"] = {}
    data[key]["transformacoes"][estado.lower()] = {
        "nome": estado,
        "hp_mult": hp_mult,
        "energia_mult": energia_mult,
        "lba_mult": lba_mult,
        "vel_add": vel_add
    }
    save(data)
    await interaction.response.send_message(
        f"✅ Transformação **{estado}** registrada para **{key}**.\n"
        f"HP ×`{hp_mult}` | Energia ×`{energia_mult}` | LBA ×`{lba_mult}` | Vel +`{vel_add}`"
    )

@tree.command(name="transformar", description="Aplica uma transformação no personagem (sempre a partir do estado base)")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação a aplicar"
)
async def transformar(interaction, nome: str, estado: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    transformacoes = char.get("transformacoes", {})
    t = transformacoes.get(estado.lower())
    if not t:
        lista = ", ".join([f"`{v['nome']}`" for v in transformacoes.values()]) or "nenhuma"
        await interaction.response.send_message(
            f"❌ Transformação **{estado}** não registrada para **{key}**.\n"
            f"Transformações disponíveis: {lista}\nUse `/registrar_transformacao` primeiro.",
            ephemeral=True
        )
        return

    historico = char.get("historico_transformacoes", [])
    if estado.lower() in [h.lower() for h in historico]:
        await interaction.response.send_message(
            f"⚠️ **{key}** já está em **{t['nome']}**. Use `/reverter` para voltar um nível ou `/base` para resetar tudo.",
            ephemeral=True
        )
        return

    # SEMPRE aplica a partir do BASE — acumula multiplicadores corretos
    hp_b = char.get("hp_base", char["hp_max"])
    en_b = char.get("energia_base", char["energia_max"])
    lba_b = char.get("lba_base", char["lba"])
    vel_b = char.get("velocidade_base", char["velocidade"])

    # Calcula multiplicadores acumulados de todas as transformações ativas + nova
    novo_historico = historico + [t["nome"]]
    hp_mult_total = 1.0
    en_mult_total = 1.0
    lba_mult_total = 1.0
    vel_add_total = 0

    for t_nome in novo_historico:
        t_data = transformacoes.get(t_nome.lower())
        if t_data:
            hp_mult_total *= t_data["hp_mult"]
            en_mult_total *= t_data["energia_mult"]
            lba_mult_total *= t_data["lba_mult"]
            vel_add_total += t_data.get("vel_add", 0)

    # Aplica a partir do base
    novo_hp_max = int(hp_b * hp_mult_total)
    novo_en_max = int(en_b * en_mult_total)

    # Mantém proporção de HP/Energia atuais
    hp_ratio = char["hp"] / char["hp_max"] if char["hp_max"] > 0 else 1
    en_ratio = char["energia"] / char["energia_max"] if char["energia_max"] > 0 else 1

    char["hp_max"] = novo_hp_max
    char["energia_max"] = novo_en_max
    char["hp"] = int(novo_hp_max * hp_ratio)
    char["energia"] = int(novo_en_max * en_ratio)
    char["lba"] = int(lba_b * lba_mult_total)
    char["velocidade"] = min(10, vel_b + vel_add_total)
    char["estado"] = t["nome"]
    char["historico_transformacoes"] = novo_historico

    save(data)
    await interaction.response.send_message(
        f"✨ **{key}** entrou em **{t['nome']}**!\n"
        f"Pilha: {' → '.join(novo_historico)}",
        embed=status_embed(key, char)
    )

@tree.command(name="reverter", description="Volta UM nível de transformação (desfaz a última)")
@app_commands.describe(nome="Nome do personagem")
async def reverter(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    historico = char.get("historico_transformacoes", [])
    if not historico:
        await interaction.response.send_message(
            f"⚠️ **{key}** já está na base. Não há transformações para reverter.",
            ephemeral=True
        )
        return

    ultimo = historico[-1]
    novo_historico = historico[:-1]
    transformacoes = char.get("transformacoes", {})

    hp_b = char.get("hp_base", char["hp_max"])
    en_b = char.get("energia_base", char["energia_max"])
    lba_b = char.get("lba_base", char["lba"])
    vel_b = char.get("velocidade_base", char["velocidade"])

    if novo_historico:
        hp_mult_total = 1.0
        en_mult_total = 1.0
        lba_mult_total = 1.0
        vel_add_total = 0
        for t_nome in novo_historico:
            t_data = transformacoes.get(t_nome.lower())
            if t_data:
                hp_mult_total *= t_data["hp_mult"]
                en_mult_total *= t_data["energia_mult"]
                lba_mult_total *= t_data["lba_mult"]
                vel_add_total += t_data.get("vel_add", 0)

        novo_hp_max = int(hp_b * hp_mult_total)
        novo_en_max = int(en_b * en_mult_total)
        hp_ratio = char["hp"] / char["hp_max"] if char["hp_max"] > 0 else 1
        en_ratio = char["energia"] / char["energia_max"] if char["energia_max"] > 0 else 1
        char["hp_max"] = novo_hp_max
        char["energia_max"] = novo_en_max
        char["hp"] = min(int(novo_hp_max * hp_ratio), novo_hp_max)
        char["energia"] = min(int(novo_en_max * en_ratio), novo_en_max)
        char["lba"] = int(lba_b * lba_mult_total)
        char["velocidade"] = min(10, vel_b + vel_add_total)
        char["estado"] = novo_historico[-1]
    else:
        # Voltou para base
        char["hp_max"] = hp_b
        char["energia_max"] = en_b
        char["hp"] = min(char["hp"], hp_b)
        char["energia"] = min(char["energia"], en_b)
        char["lba"] = lba_b
        char["velocidade"] = vel_b
        char["estado"] = "Base"

    char["historico_transformacoes"] = novo_historico
    save(data)
    await interaction.response.send_message(
        f"🔄 **{key}** reverteu **{ultimo}**.\n"
        f"Estado atual: `{'Base' if not novo_historico else novo_historico[-1]}`",
        embed=status_embed(key, char)
    )

@tree.command(name="base", description="Reverte o personagem completamente para o estado base (remove todas as transformações)")
@app_commands.describe(nome="Nome do personagem")
async def base(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    hp_b = char.get("hp_base", char["hp_max"])
    en_b = char.get("energia_base", char["energia_max"])
    lba_b = char.get("lba_base", char["lba"])
    vel_b = char.get("velocidade_base", char["velocidade"])

    char["hp_max"] = hp_b
    char["energia_max"] = en_b
    char["hp"] = min(char["hp"], hp_b)
    char["energia"] = min(char["energia"], en_b)
    char["lba"] = lba_b
    char["velocidade"] = vel_b
    char["estado"] = "Base"
    char["historico_transformacoes"] = []
    save(data)
    await interaction.response.send_message(
        f"🔄 **{key}** voltou ao estado **Base** (todas as transformações removidas).",
        embed=status_embed(key, char)
    )

@tree.command(name="resetar", description="Reseta HP, energia e evasivas para o máximo do estado atual")
@app_commands.describe(nome="Nome do personagem")
async def resetar(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    char["hp"] = char["hp_max"]
    char["energia"] = char["energia_max"]
    char["evasivas"] = 5
    save(data)
    await interaction.response.send_message(
        f"♻️ **{key}** HP e energia resetados para o máximo do estado atual (`{char['estado']}`).",
        embed=status_embed(key, char)
    )

@tree.command(name="listar_transformacoes", description="Lista todas as transformações registradas de um personagem")
@app_commands.describe(nome="Nome do personagem")
async def listar_transformacoes(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    transformacoes = data[key].get("transformacoes", {})
    if not transformacoes:
        await interaction.response.send_message(f"**{key}** não tem transformações registradas.", ephemeral=True)
        return
    embed = discord.Embed(title=f"✨ Transformações de {key}", color=0x4a7fff)
    for t in transformacoes.values():
        embed.add_field(
            name=t["nome"],
            value=f"HP ×`{t['hp_mult']}` | Energia ×`{t['energia_mult']}` | LBA ×`{t['lba_mult']}` | Vel +`{t.get('vel_add', 0)}`",
            inline=False
        )
    historico = data[key].get("historico_transformacoes", [])
    if historico:
        embed.add_field(name="Ativas agora", value=" → ".join(historico), inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="deletar_transformacao", description="Remove uma transformação registrada de um personagem")
@app_commands.describe(nome="Nome do personagem", estado="Nome da transformação a deletar")
async def deletar_transformacao(interaction, nome: str, estado: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    transformacoes = data[key].get("transformacoes", {})
    t_key = estado.lower()
    if t_key not in transformacoes:
        lista = ", ".join([f"`{v['nome']}`" for v in transformacoes.values()]) or "nenhuma"
        await interaction.response.send_message(
            f"❌ Transformação **{estado}** não encontrada em **{key}**.\nRegistradas: {lista}",
            ephemeral=True
        )
        return
    nome_real = transformacoes[t_key]["nome"]
    del data[key]["transformacoes"][t_key]
    save(data)
    await interaction.response.send_message(f"🗑️ Transformação **{nome_real}** removida de **{key}**.")

# ════════════════════════════════════════════
# REIATSU
# ════════════════════════════════════════════

@tree.command(name="comparar_reiatsu", description="Compara o reiatsu de dois personagens (Controle, Reinos, Impacto)")
@app_commands.describe(nome1="Primeiro personagem", nome2="Segundo personagem")
async def comparar_reiatsu(interaction, nome1: str, nome2: str):
    data = load()
    k1 = get_key(data, nome1)
    k2 = get_key(data, nome2)
    if not k1 or not k2:
        await interaction.response.send_message("❌ Um dos personagens não foi encontrado.", ephemeral=True)
        return

    r1 = data[k1].get("reiatsu", 0)
    r2 = data[k2].get("reiatsu", 0)

    controle, reino, impacto = analisar_reiatsu(r1, r2, k1, k2)

    embed = discord.Embed(title="🔥 COMPARAÇÃO DE REIATSU", color=0xff6600)
    embed.add_field(name=k1, value=f"`{r1:,}` reiatsu", inline=True)
    embed.add_field(name=k2, value=f"`{r2:,}` reiatsu", inline=True)
    embed.add_field(name="Diferença", value=f"`{abs(r1 - r2):,}`", inline=True)
    embed.add_field(name="\u200b", value=controle, inline=False)
    embed.add_field(name="\u200b", value=reino, inline=False)
    embed.add_field(name="\u200b", value=impacto, inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="reiatsu_tabela", description="Exibe a tabela de reiatsu por tipo de ser")
async def reiatsu_tabela(interaction):
    embed = discord.Embed(title="📊 TABELA DE REIATSU", color=0xff6600,
        description="Referência de valores fixos por categoria de ser.")
    embed.add_field(name="10.000", value="Shinigamis sem domínio algum", inline=False)
    embed.add_field(name="20.000", value="Qualquer demônio ou Glichborn básico", inline=False)
    embed.add_field(name="30.000", value="Demônio/Glichborn de nível médio na hierarquia OU híbrido de 2 raças (Shinigami + uma das duas)", inline=False)
    embed.add_field(name="40.000", value="A um grau do topo da hierarquia (demônios/Glichborns) OU híbrido de 3 raças", inline=False)
    embed.add_field(name="50.000", value="Arrankars OU híbridos de 4 raças", inline=False)
    embed.add_field(name="60.000", value="Vasto Lordes (como Tamsy) OU Shinigami híbrido de Vasto Lorde + outras raças", inline=False)
    embed.add_field(name="70.000", value="Categoria anterior + Shikai dominado", inline=False)
    embed.add_field(name="80.000", value="Categoria anterior + Bankai", inline=False)
    embed.add_field(name="90.000 – 100.000", value="Seres no auge absoluto (Xay, Kyoga, Namegog, etc.) — presença passiva já pode matar", inline=False)
    await interaction.response.send_message(embed=embed)

# ════════════════════════════════════════════
# CONTROLE
# ════════════════════════════════════════════

@tree.command(name="controle_gastar", description="Gasta pontos de controle ao usar técnica de manipulação/corpo")
@app_commands.describe(
    nome="Nome do personagem",
    pontos="Quantidade de pontos a gastar (padrão: 1)",
    oponente="(Opcional) Nome do oponente para verificar diferença de reiatsu"
)
async def controle_gastar(interaction, nome: str, pontos: app_commands.Range[int, 1, 5] = 1, oponente: str = None):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    controle_atual = char.get("controle", 3)

    custo_extra = 0
    aviso_reiatsu = ""

    if oponente:
        k2 = get_key(data, oponente)
        if k2:
            r1 = char.get("reiatsu", 0)
            r2 = data[k2].get("reiatsu", 0)
            diff = r2 - r1  # positivo = oponente é mais forte
            if diff >= 30000:
                await interaction.response.send_message(
                    f"❌ **{key}** não pode controlar **{k2}** — diferença de reiatsu extrema (`{diff:,}`). Técnica **falha automaticamente**.",
                    ephemeral=True
                )
                return
            elif diff >= 20000:
                custo_extra = 1
                aviso_reiatsu = f"\n⚠️ Reiatsu inferior em `{diff:,}` — custo +1 ponto extra."

    custo_total = pontos + custo_extra
    antes = controle_atual
    char["controle"] = controle_atual - custo_total
    save(data)

    msg = f"🔒 **{key}** gastou `{custo_total}` ponto(s) de controle.\n`Controle: {antes} → {char['controle']}`{aviso_reiatsu}"
    if char["controle"] <= 0:
        msg += f"\n🔴 **CONTROLE NEGATIVO — TÉCNICAS DE CONTROLE FALHAM!**"
    await interaction.response.send_message(msg, embed=status_embed(key, char))

@tree.command(name="controle_set", description="Define manualmente os pontos de controle de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Novo valor de controle")
async def controle_set(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    data[key]["controle"] = valor
    save(data)
    await interaction.response.send_message(
        f"🔒 **{key}** controle → `{valor}`",
        embed=status_embed(key, data[key])
    )

# ════════════════════════════════════════════
# HADO DE APOSTA
# ════════════════════════════════════════════

@tree.command(name="hado_aposta", description="Declara o Hado de Aposta — zera energia de ambos e inicia conflito de ringue")
@app_commands.describe(
    declarante="Quem declara o Hado de Aposta",
    alvo="Quem recebe o Hado de Aposta"
)
async def hado_aposta(interaction, declarante: str, alvo: str):
    data = load()
    k1 = get_key(data, declarante)
    k2 = get_key(data, alvo)
    if not k1 or not k2:
        await interaction.response.send_message("❌ Um dos personagens não foi encontrado.", ephemeral=True)
        return

    char1 = data[k1]
    char2 = data[k2]

    # Guarda energia atual para restaurar depois
    char1["energia_pre_aposta"] = char1.get("energia", 0)
    char2["energia_pre_aposta"] = char2.get("energia", 0)

    # Zera energia de ambos
    char1["energia"] = 0
    char2["energia"] = 0

    save(data)

    embed = discord.Embed(
        title="⚔️ HADO DE APOSTA DECLARADO",
        description=(
            f"**{k1}** lançou o **Hado de Aposta** contra **{k2}**!\n\n"
            f"A energia amaldiçoada de ambos foi selada.\n"
            f"O conflito de ringue começa agora — **apenas artes marciais**.\n"
            f"Sem técnicas, sem transformações adicionais.\n\n"
            f"Quando o ringue terminar, use `/hado_resultado` para registrar o vencedor."
        ),
        color=0xff0000
    )
    embed.add_field(name=k1, value=f"Energia selada: `{char1['energia_pre_aposta']:,}`\nControle: `{char1.get('controle', 3)}`", inline=True)
    embed.add_field(name=k2, value=f"Energia selada: `{char2['energia_pre_aposta']:,}`\nControle: `{char2.get('controle', 3)}`", inline=True)
    embed.add_field(
        name="Regras do Ringue",
        value=(
            "• Avaliado objetivamente por número de golpes e qualidade\n"
            "• Vencedor: recupera `3` pontos de controle\n"
            "• Perdedor: perde `1` ponto de controle (pode negativar)\n"
            "• Energia restaurada ao fim do ringue"
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="hado_resultado", description="Registra o resultado do Hado de Aposta e aplica pontos de controle")
@app_commands.describe(
    vencedor="Nome do vencedor do ringue",
    perdedor="Nome do perdedor do ringue"
)
async def hado_resultado(interaction, vencedor: str, perdedor: str):
    data = load()
    kv = get_key(data, vencedor)
    kp = get_key(data, perdedor)
    if not kv or not kp:
        await interaction.response.send_message("❌ Um dos personagens não foi encontrado.", ephemeral=True)
        return

    char_v = data[kv]
    char_p = data[kp]

    # Restaura energia
    char_v["energia"] = char_v.pop("energia_pre_aposta", char_v.get("energia_max", 0))
    char_p["energia"] = char_p.pop("energia_pre_aposta", char_p.get("energia_max", 0))

    # Vencedor: +3 controle (com cap no base)
    ctrl_base_v = char_v.get("controle_base", 3)
    ctrl_v_antes = char_v.get("controle", 3)
    ctrl_neg = ctrl_v_antes  # antes era negativo?

    if ctrl_neg < 0:
        # Em negativo: recupera menos dependendo do quão negativo está
        if ctrl_neg <= -3:
            recupera = 0
        elif ctrl_neg == -2:
            recupera = 1
        elif ctrl_neg == -1:
            recupera = 2
        else:
            recupera = 3
        char_v["controle"] = ctrl_neg + recupera
    else:
        char_v["controle"] = min(ctrl_base_v, ctrl_v_antes + 3)

    # Perdedor: -1 controle
    ctrl_p_antes = char_p.get("controle", 3)
    char_p["controle"] = ctrl_p_antes - 1

    save(data)

    embed = discord.Embed(
        title="🏆 RESULTADO DO HADO DE APOSTA",
        color=0x00ff88
    )
    embed.add_field(
        name=f"🏆 {kv} — VENCEDOR",
        value=(
            f"Energia restaurada: `{char_v['energia']:,}`\n"
            f"Controle: `{ctrl_v_antes}` → `{char_v['controle']}`"
            + (f" (recuperou `{char_v['controle'] - ctrl_v_antes}`)" if char_v['controle'] > ctrl_v_antes else "")
        ),
        inline=False
    )
    embed.add_field(
        name=f"💀 {kp} — PERDEDOR",
        value=(
            f"Energia restaurada: `{char_p['energia']:,}`\n"
            f"Controle: `{ctrl_p_antes}` → `{char_p['controle']}`"
            + (f"\n🔴 **CONTROLE NEGATIVO!**" if char_p['controle'] <= 0 else "")
        ),
        inline=False
    )

    if char_p["controle"] < 0:
        neg = char_p["controle"]
        if neg <= -3:
            prox = "0 pontos"
        elif neg == -2:
            prox = "1 ponto"
        elif neg == -1:
            prox = "2 pontos"
        embed.add_field(
            name="⚠️ Penalidade de controle negativo",
            value=(
                f"**{kp}** está em `{neg}` de controle.\n"
                f"Técnicas de controle **falham automaticamente**.\n"
                f"Se ganhar o próximo Hado de Aposta, recupera **{prox}** de controle."
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ════════════════════════════════════════════
# STATS ESPECIAIS
# ════════════════════════════════════════════

@tree.command(name="extra_set", description="Define um stat especial do personagem (ex: Queimadura, Corda)")
@app_commands.describe(
    nome="Nome do personagem",
    campo="Nome do stat especial (ex: Queimadura)",
    valor="Valor do stat (ex: 50%)"
)
async def extra_set(interaction, nome: str, campo: str, valor: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    if "extras" not in data[key]:
        data[key]["extras"] = {}
    data[key]["extras"][campo] = valor
    save(data)
    await interaction.response.send_message(
        f"📌 **{key}** — {campo} → `{valor}`",
        embed=status_embed(key, data[key])
    )

@tree.command(name="extra_remover", description="Remove um stat especial do personagem")
@app_commands.describe(nome="Nome do personagem", campo="Nome do stat a remover")
async def extra_remover(interaction, nome: str, campo: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    extras = data[key].get("extras", {})
    if campo not in extras:
        await interaction.response.send_message(f"❌ Stat **{campo}** não encontrado em **{key}**.", ephemeral=True)
        return
    del data[key]["extras"][campo]
    save(data)
    await interaction.response.send_message(
        f"🗑️ **{campo}** removido de **{key}**.",
        embed=status_embed(key, data[key])
    )

# ════════════════════════════════════════════
# AJUDA
# ════════════════════════════════════════════

@tree.command(name="ajuda", description="Lista todos os comandos disponíveis")
async def ajuda(interaction):
    embed = discord.Embed(title="◈ FINAL DO VOID — BOT DE COMBATE v7", color=0x4a7fff)
    embed.add_field(name="📋 PERSONAGENS", value=
        "`/registrar` — cria personagem\n"
        "`/status [nome]` — status atual\n"
        "`/todos` — todos os personagens\n"
        "`/resetar [nome]` — reseta HP e energia pro máximo atual\n"
        "`/deletar [nome]` — remove personagem",
        inline=False)
    embed.add_field(name="⚔️ COMBATE", value=
        "`/dano [nome] [valor]` — aplica dano no HP\n"
        "`/curar [nome] [valor]` — cura HP\n"
        "`/gastar [nome] [valor]` — gasta energia amaldiçoada\n"
        "`/recuperar [nome] [valor]` — recupera energia\n"
        "`/velocidade [nome] [1-10]` — altera velocidade\n"
        "`/lba [nome] [valor]` — altera LBA",
        inline=False)
    embed.add_field(name="💨 EVASIVAS", value=
        "`/evasiva_usar [nome] [qtd]` — gasta evasivas\n"
        "`/evasiva_recuperar [nome]` — recupera (base 5)\n"
        "`/evasiva_recuperar [nome] [oponente]` — recupera com bônus de vel.\n"
        "`/comparar_velocidade [nome1] [nome2]` — compara vel. e evasivas",
        inline=False)
    embed.add_field(name="✨ TRANSFORMAÇÕES", value=
        "`/registrar_transformacao` — cadastra transformação\n"
        "`/transformar [nome] [estado]` — aplica transformação (empilhável)\n"
        "`/reverter [nome]` — desfaz a ÚLTIMA transformação\n"
        "`/base [nome]` — volta TUDO para o estado base\n"
        "`/listar_transformacoes [nome]` — lista transformações\n"
        "`/deletar_transformacao [nome] [estado]` — remove transformação",
        inline=False)
    embed.add_field(name="🔥 REIATSU", value=
        "`/comparar_reiatsu [nome1] [nome2]` — Controle, Reinos e Impacto\n"
        "`/reiatsu_tabela` — tabela de reiatsu por tipo de ser",
        inline=False)
    embed.add_field(name="🔒 CONTROLE", value=
        "`/controle_gastar [nome] [pontos] [oponente?]` — gasta controle\n"
        "`/controle_set [nome] [valor]` — define controle manualmente",
        inline=False)
    embed.add_field(name="⚡ HADO DE APOSTA", value=
        "`/hado_aposta [declarante] [alvo]` — declara o Hado (zera energia)\n"
        "`/hado_resultado [vencedor] [perdedor]` — finaliza ringue e redistribui controle",
        inline=False)
    embed.add_field(name="📌 STATS ESPECIAIS", value=
        "`/extra_set [nome] [campo] [valor]` — define stat único\n"
        "`/extra_remover [nome] [campo]` — remove stat único",
        inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)

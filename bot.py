bash

cat > /home/claude/bot.py << 'PYEOF'
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

# ════════════════════════════════
# DATA
# ════════════════════════════════
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

# ════════════════════════════════
# HELPERS DE CÁLCULO
# ════════════════════════════════

# ── EVASIVAS por diferença de velocidade ──
def calcular_evasivas_bonus(vel_propria, vel_oponente):
    diff = vel_propria - vel_oponente
    if diff <= 0:   return 5
    elif diff <= 1: return 5
    elif diff <= 3: return 7
    elif diff <= 5: return 9
    else:           return 10

def calcular_evasivas_penalidade(vel_propria, vel_oponente):
    diff = vel_oponente - vel_propria
    if diff >= 6: return 3
    return 5

# ── REIATSU: Controle ──
def calcular_controle_base(reiatsu):
    """Base sempre 3. Reiatsu alto dá bônus."""
    if reiatsu >= 80000: return 5
    if reiatsu >= 60000: return 4
    return 3

def controle_gasto(reiatsu_atacante, reiatsu_alvo):
    """Quanto gasta ao usar técnica de controle. Diferença pode reduzir custo."""
    diff = reiatsu_atacante - reiatsu_alvo
    if diff >= 30000: return 0   # domínio total — não gasta
    if diff >= 20000: return 0   # vantagem alta — não gasta
    if diff >= 10000: return 1   # vantagem pequena — gasto normal
    if diff >= 0:     return 1   # empate — gasto normal
    if diff >= -10000: return 2  # desvantagem pequena — gasta 2
    return 3                     # desvantagem grande — gasta 3 (pode negativar)

def recuperar_controle_apos_aposta(pontos_atuais, ganhou):
    """Recuperação pós Hado de Aposta. Considera negativo."""
    if ganhou:
        if pontos_atuais >= 0:   return min(calcular_controle_base(0) + 2, pontos_atuais + 3)
        if pontos_atuais == -1:  return pontos_atuais + 2
        if pontos_atuais == -2:  return pontos_atuais + 1
        return pontos_atuais  # -3 ou pior: fica travado por esse Aposta
    else:
        return pontos_atuais - 1  # perde 1 (pode negativar)

# ── REIATSU: Conflito de Reinos ──
def avaliar_conflito_reinos(r1, r2, nome1, nome2):
    diff = abs(r1 - r2)
    mais_forte = nome1 if r1 >= r2 else nome2
    mais_fraco = nome2 if r1 >= r2 else nome1
    if diff >= 30000:
        return (f"🌌 **Domínio Automático** — {mais_forte} se expande sem resistência. "
                f"{mais_fraco} não consegue expandir seu domínio neste conflito.")
    elif diff >= 20000:
        return (f"⚡ **Vantagem Alta** — {mais_forte} tem dominação clara. "
                f"{mais_fraco} enfrenta resistência severa ao expandir.")
    elif diff >= 10000:
        return (f"📊 **Vantagem Pequena** — {mais_forte} tem leve superioridade no conflito de reinos. "
                f"Conflito real mas inclinado.")
    else:
        return f"⚔️ **Conflito Real** — Nenhum lado tem vantagem automática. Resultado depende das técnicas."

# ── REIATSU: Impacto ──
def avaliar_impacto_reiatsu(r_atacante, r_alvo, nome_atacante, nome_alvo):
    diff = r_atacante - r_alvo
    if diff >= 50000:
        return (f"☠️ **IMPACTO LETAL** — A presença de {nome_atacante} é fisicamente destrutiva para {nome_alvo}. "
                f"Aproximação causa dano direto. Comparável ao Helt Coyote (90k).")
    elif diff >= 30000:
        return (f"💀 **IMPACTO SEVERO** — {nome_alvo} sente a pressão espiritual como força física. "
                f"Movimentação comprometida, dificuldade grave em combate.")
    elif diff >= 20000:
        return (f"⚠️ **IMPACTO ALTO** — {nome_alvo} sente peso real da presença de {nome_atacante}. "
                f"Pequena penalidade na agilidade e concentração.")
    elif diff >= 10000:
        return (f"📉 **IMPACTO LEVE** — {nome_alvo} percebe a diferença de pressão. "
                f"Efeito mínimo em combate mas presente.")
    elif diff > 0:
        return f"〰️ **Diferença mínima** — Pouco impacto perceptível."
    else:
        return f"✅ **Sem impacto** — {nome_alvo} tem Reiatsu igual ou superior. Nenhuma pressão."

# ════════════════════════════════
# SISTEMA DE TRANSFORMAÇÕES (EMPILHAMENTO CORRETO)
# ════════════════════════════════
def aplicar_transformacao(char, transformacao):
    """
    Aplica transformação sempre sobre os stats BASE, não sobre os atuais.
    Isso resolve o problema de empilhar transformações.
    """
    char["estado"] = transformacao["nome"]
    char["estado_stack"] = char.get("estado_stack", [])
    
    # Sempre calcula sobre a base
    hp_base   = char["hp_base"]
    en_base   = char["energia_base"]
    lba_base  = char["lba_base"]
    vel_base  = char["velocidade_base"]

    # Aplica o multiplicador desta transformação
    novo_hp_max  = int(hp_base  * transformacao["hp_mult"])
    novo_en_max  = int(en_base  * transformacao["energia_mult"])
    novo_lba     = int(lba_base * transformacao["lba_mult"])
    nova_vel     = min(10, vel_base + transformacao.get("vel_add", 0))

    # Mantém proporção de HP e Energia atuais
    if char["hp_max"] > 0:
        hp_ratio = char["hp"] / char["hp_max"]
    else:
        hp_ratio = 1.0
    if char["energia_max"] > 0:
        en_ratio = char["energia"] / char["energia_max"]
    else:
        en_ratio = 1.0

    char["hp_max"]      = novo_hp_max
    char["hp"]          = int(novo_hp_max * hp_ratio)
    char["energia_max"] = novo_en_max
    char["energia"]     = int(novo_en_max * en_ratio)
    char["lba"]         = novo_lba
    char["velocidade"]  = nova_vel

def reverter_base(char):
    """Reverte para os stats base completamente."""
    char["estado"]     = "Base"
    char["hp_max"]     = char["hp_base"]
    char["energia_max"]= char["energia_base"]
    char["lba"]        = char["lba_base"]
    char["velocidade"] = char["velocidade_base"]
    # Mantém HP e energia na proporção atual
    char["hp"]         = min(char["hp"],     char["hp_max"])
    char["energia"]    = min(char["energia"], char["energia_max"])

# ════════════════════════════════
# EMBED DE STATUS
# ════════════════════════════════
def status_embed(name, char):
    estado = char.get("estado", "Base")
    cor = 0x4a7fff if estado == "Base" else 0xe03060

    hp_max = char.get("hp_max", char.get("hp", 0))
    en_max = char.get("energia_max", char.get("energia", 0))
    hp     = char.get("hp", 0)
    en     = char.get("energia", 0)
    hp_pct = int((hp / hp_max * 100)) if hp_max > 0 else 0
    en_pct = int((en / en_max * 100)) if en_max > 0 else 0

    vel      = char.get("velocidade", 0)
    evasivas = char.get("evasivas", 5)
    controle = char.get("controle", 3)
    reiatsu  = char.get("reiatsu", 0)

    def barra(pct):
        filled = int(pct / 10)
        return "█" * filled + "░" * (10 - filled) + f" {pct}%"

    def barra_evasivas(atual, maximo=10):
        atual = max(0, atual)
        return "◆" * min(atual, maximo) + "◇" * (maximo - min(atual, maximo)) + f" {atual}"

    def barra_controle(atual):
        cor_c = "🟢" if atual >= 2 else ("🟡" if atual == 1 else "🔴")
        return f"{cor_c} `{atual}` ponto(s)"

    embed = discord.Embed(title=f"◈ {name}", color=cor)
    embed.add_field(name="Estado",      value=f"`{estado}`",          inline=True)
    embed.add_field(name="Reiatsu",     value=f"`{reiatsu:,}`",       inline=True)
    embed.add_field(name="Velocidade",  value=f"`{vel}/10`",          inline=True)
    embed.add_field(name=f"HP [{hp:,} / {hp_max:,}]",        value=barra(hp_pct), inline=False)
    embed.add_field(name=f"Energia [{en:,} / {en_max:,}]",   value=barra(en_pct), inline=False)
    embed.add_field(name="LBA",         value=f"`{char.get('lba', 0):,}`", inline=True)
    embed.add_field(name="Evasivas",    value=barra_evasivas(evasivas),    inline=True)
    embed.add_field(name="Controle",    value=barra_controle(controle),    inline=True)

    extras = char.get("extras", {})
    if extras:
        for k, v in extras.items():
            embed.add_field(name=k, value=f"`{v}`", inline=True)

    alertas = []
    if hp_pct <= 20:    alertas.append("⚠️ HP CRÍTICO")
    if en_pct <= 10:    alertas.append("⚠️ ENERGIA CRÍTICA")
    if en <= 0:         alertas.append("☠️ ENERGIA ZERADA — PERSONAGEM INATIVO")
    if evasivas == 0:   alertas.append("💨 SEM EVASIVAS")
    if controle <= 0:   alertas.append("🔴 CONTROLE NEGATIVO — TÉCNICAS DE CONTROLE FALHAM")
    if alertas:
        embed.add_field(name="ALERTAS", value="\n".join(alertas), inline=False)

    return embed

# ════════════════════════════════
# SINCRONIZAR
# ════════════════════════════════
@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Bot online: {bot.user} | Comandos: {len(synced)}")
    except Exception as e:
        print(f"Erro sync: {e}")

@tree.command(name="sync", description="[ADMIN] Força sincronização dos comandos")
async def sync_cmd(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
        return
    tree.copy_global_to(guild=guild)
    synced = await tree.sync(guild=guild)
    await interaction.response.send_message(f"✅ {len(synced)} comandos sincronizados.", ephemeral=True)

# ════════════════════════════════
# PERSONAGENS
# ════════════════════════════════

@tree.command(name="registrar", description="Registra um personagem no sistema")
@app_commands.describe(
    nome="Nome do personagem",
    hp="HP máximo",
    energia="Energia amaldiçoada máxima",
    reiatsu="Reiatsu fixo (10.000 a 100.000)",
    lba="LBA base",
    velocidade="Velocidade de 1 a 10"
)
async def registrar(interaction, nome: str, hp: int, energia: int, reiatsu: int, lba: int,
                    velocidade: app_commands.Range[int, 1, 10]):
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
        # Stats base (nunca mudam, usados para calcular transformações)
        "hp_base": hp,
        "energia_base": energia,
        "lba_base": lba,
        "velocidade_base": velocidade,
        "controle_base": controle_base,
        # Dados
        "transformacoes": {},
        "extras": {}
    }
    save(data)
    await interaction.response.send_message(
        f"✅ **{nome}** registrado! Controle base: `{controle_base}` (Reiatsu `{reiatsu:,}`)",
        embed=status_embed(nome, data[nome])
    )

@tree.command(name="status", description="Mostra o status de um personagem")
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
        await interaction.response.send_message("Nenhum personagem registrado.")
        return
    await interaction.response.defer()
    for nome, char in data.items():
        await interaction.followup.send(embed=status_embed(nome, char))

# ════════════════════════════════
# COMBATE — HP E ENERGIA
# ════════════════════════════════

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
    await interaction.response.send_message(
        f"💥 **{key}** recebeu `{antes - char['hp']:,}` de dano.\n`HP: {antes:,} → {char['hp']:,}`",
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
    await interaction.response.send_message(
        f"💚 **{key}** recuperou `{char['hp'] - antes:,}` de HP.\n`HP: {antes:,} → {char['hp']:,}`",
        embed=status_embed(key, char)
    )

@tree.command(name="gastar", description="Gasta energia amaldiçoada")
@app_commands.describe(nome="Nome do personagem", valor="Quantidade gasta")
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
    msg = f"⚡ **{key}** gastou `{antes - char['energia']:,}` de energia.\n`Energia: {antes:,} → {char['energia']:,}`"
    if char["energia"] == 0:
        msg += "\n☠️ **ENERGIA ZERADA — PERSONAGEM INATIVO**"
    await interaction.response.send_message(msg, embed=status_embed(key, char))

@tree.command(name="recuperar", description="Recupera energia amaldiçoada")
@app_commands.describe(nome="Nome do personagem", valor="Quantidade recuperada")
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
    await interaction.response.send_message(
        f"🔵 **{key}** recuperou `{char['energia'] - antes:,}` de energia.\n`Energia: {antes:,} → {char['energia']:,}`",
        embed=status_embed(key, char)
    )

@tree.command(name="lba", description="Altera o LBA de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Novo valor de LBA")
async def lba_cmd(interaction, nome: str, valor: int):
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

@tree.command(name="velocidade", description="Altera a velocidade de um personagem (1-10)")
@app_commands.describe(nome="Nome do personagem", valor="Nova velocidade")
async def velocidade_cmd(interaction, nome: str, valor: app_commands.Range[int, 1, 10]):
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

# ════════════════════════════════
# EVASIVAS
# ════════════════════════════════

@tree.command(name="evasiva_usar", description="Registra o uso de evasivas")
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
            f"❌ **{key}** não tem evasivas. Use `/evasiva_recuperar`.", ephemeral=True)
        return
    char["evasivas"] = max(0, antes - quantidade)
    save(data)
    msg = f"💨 **{key}** usou `{quantidade}` evasiva(s).\n`{antes} → {char['evasivas']}`"
    if char["evasivas"] == 0:
        msg += "\n💨 **SEM EVASIVAS — use técnica de velocidade para recuperar**"
    await interaction.response.send_message(msg, embed=status_embed(key, char))

@tree.command(name="evasiva_recuperar", description="Recupera evasivas. Com oponente: calcula bônus de velocidade.")
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
        key2 = get_key(data, oponente)
        if not key2:
            await interaction.response.send_message(f"❌ **{oponente}** não encontrado.", ephemeral=True)
            return
        v2 = data[key2].get("velocidade", 5)
        novas = calcular_evasivas_bonus(v1, v2) if v1 >= v2 else calcular_evasivas_penalidade(v1, v2)
        msg_extra = f"vs **{key2}** (vel `{v2}/10`) → `{novas}` evasivas"
    else:
        novas = 5
        msg_extra = "recuperação base → `5` evasivas"

    char["evasivas"] = novas
    save(data)
    await interaction.response.send_message(
        f"💨 **{key}** recuperou evasivas ({msg_extra}).",
        embed=status_embed(key, char)
    )

@tree.command(name="comparar_velocidade", description="Compara velocidade e evasivas entre dois personagens")
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
    ev1 = calcular_evasivas_bonus(v1, v2) if v1 >= v2 else calcular_evasivas_penalidade(v1, v2)
    ev2 = calcular_evasivas_bonus(v2, v1) if v2 >= v1 else calcular_evasivas_penalidade(v2, v1)

    embed = discord.Embed(title="💨 COMPARAÇÃO DE VELOCIDADE", color=0x4a7fff)
    embed.add_field(name=k1, value=f"Vel: `{v1}/10` | Evasivas ao rec.: `{ev1}`", inline=True)
    embed.add_field(name=k2, value=f"Vel: `{v2}/10` | Evasivas ao rec.: `{ev2}`", inline=True)
    embed.add_field(name="Diferença", value=f"`{diff}` ponto(s)", inline=False)

    if diff == 0:
        res = "Empate — ambos com 5 evasivas base."
    elif diff <= 1:
        res = "Empate prático. Sem vantagem real."
    elif diff <= 3:
        res = f"**{''.join([k1 if v1 > v2 else k2])}** tem vantagem leve (+2 evasivas)."
    elif diff <= 5:
        res = f"**{''.join([k1 if v1 > v2 else k2])}** tem vantagem clara (+4 evasivas)."
    else:
        mais = k1 if v1 > v2 else k2
        menos = k2 if v1 > v2 else k1
        res = f"**{mais}** domina (+5 evasivas). **{menos}** cai para 3 evasivas."
    embed.add_field(name="Resultado", value=res, inline=False)
    await interaction.response.send_message(embed=embed)

# ════════════════════════════════
# TRANSFORMAÇÕES — SISTEMA CORRIGIDO
# ════════════════════════════════

@tree.command(name="registrar_transformacao", description="Registra uma transformação (calculada sempre sobre a base)")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação (ex: Shikai, Bankai)",
    hp_mult="Multiplicador de HP sobre a base. Ex: 1.5 = +50%. Use 1 pra não mudar.",
    energia_mult="Multiplicador de Energia sobre a base.",
    lba_mult="Multiplicador de LBA sobre a base.",
    vel_add="Pontos de velocidade a adicionar ao valor base."
)
async def registrar_transformacao(interaction, nome: str, estado: str,
                                   hp_mult: float, energia_mult: float,
                                   lba_mult: float, vel_add: int):
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
    # Mostra como ficaria sobre a base
    base = data[key]
    hp_prev  = int(base["hp_base"]       * hp_mult)
    en_prev  = int(base["energia_base"]  * energia_mult)
    lba_prev = int(base["lba_base"]      * lba_mult)
    vel_prev = min(10, base["velocidade_base"] + vel_add)
    await interaction.response.send_message(
        f"✅ Transformação **{estado}** registrada para **{key}**.\n"
        f"*(Calculada sempre sobre a base, nunca empilha)*\n"
        f"HP: `{base['hp_base']:,}` → `{hp_prev:,}` | "
        f"Energia: `{base['energia_base']:,}` → `{en_prev:,}` | "
        f"LBA: `{base['lba_base']:,}` → `{lba_prev:,}` | "
        f"Vel: `{base['velocidade_base']}` → `{vel_prev}/10`"
    )

@tree.command(name="transformar", description="Aplica uma transformação (sempre sobre a base, sem empilhar)")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação, ou 'base' para reverter"
)
async def transformar(interaction, nome: str, estado: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]

    if estado.lower() == "base":
        reverter_base(char)
        save(data)
        await interaction.response.send_message(
            f"🔄 **{key}** reverteu para **Base**.",
            embed=status_embed(key, char)
        )
        return

    transformacoes = char.get("transformacoes", {})
    t = transformacoes.get(estado.lower())
    if not t:
        lista = ", ".join([f"`{v['nome']}`" for v in transformacoes.values()]) or "nenhuma"
        await interaction.response.send_message(
            f"❌ Transformação **{estado}** não encontrada em **{key}**.\n"
            f"Registradas: {lista}\nUse `/registrar_transformacao` primeiro.",
            ephemeral=True
        )
        return

    estado_anterior = char.get("estado", "Base")
    aplicar_transformacao(char, t)
    save(data)
    await interaction.response.send_message(
        f"✨ **{key}**: `{estado_anterior}` → **{t['nome']}** *(calculado sobre a base)*",
        embed=status_embed(key, char)
    )

@tree.command(name="listar_transformacoes", description="Lista todas as transformações de um personagem")
@app_commands.describe(nome="Nome do personagem")
async def listar_transformacoes(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    transformacoes = char.get("transformacoes", {})
    if not transformacoes:
        await interaction.response.send_message(f"**{key}** não tem transformações registradas.", ephemeral=True)
        return
    embed = discord.Embed(title=f"✨ Transformações de {key}", color=0x4a7fff,
                          description=f"*Todas calculadas sobre a base de {key}*")
    for t in transformacoes.values():
        hp_prev  = int(char["hp_base"]       * t["hp_mult"])
        en_prev  = int(char["energia_base"]  * t["energia_mult"])
        lba_prev = int(char["lba_base"]      * t["lba_mult"])
        vel_prev = min(10, char["velocidade_base"] + t.get("vel_add", 0))
        embed.add_field(
            name=t["nome"],
            value=(f"HP base→ `{hp_prev:,}` | Energia→ `{en_prev:,}` | "
                   f"LBA→ `{lba_prev:,}` | Vel→ `{vel_prev}/10`\n"
                   f"*(×`{t['hp_mult']}` HP | ×`{t['energia_mult']}` En | ×`{t['lba_mult']}` LBA | +`{t.get('vel_add',0)}` Vel)*"),
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@tree.command(name="deletar_transformacao", description="Remove uma transformação registrada")
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
            f"❌ **{estado}** não encontrada em **{key}**.\nRegistradas: {lista}", ephemeral=True)
        return
    nome_real = transformacoes[t_key]["nome"]
    del data[key]["transformacoes"][t_key]
    save(data)
    await interaction.response.send_message(f"🗑️ Transformação **{nome_real}** removida de **{key}**.")

# ════════════════════════════════
# SISTEMA DE REIATSU
# ════════════════════════════════

@tree.command(name="comparar_reiatsu", description="Compara Reiatsu entre dois personagens — Controle, Reinos e Impacto")
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
    diff = abs(r1 - r2)
    mais_forte = k1 if r1 >= r2 else k2
    mais_fraco = k2 if r1 >= r2 else k1

    # Custo de controle de cada um contra o outro
    custo_1v2 = controle_gasto(r1, r2)
    custo_2v1 = controle_gasto(r2, r1)

    embed = discord.Embed(title="🔮 COMPARAÇÃO DE REIATSU", color=0xc8a020)
    embed.add_field(name=k1, value=f"`{r1:,}` Reiatsu | Controle base: `{calcular_controle_base(r1)}`", inline=True)
    embed.add_field(name=k2, value=f"`{r2:,}` Reiatsu | Controle base: `{calcular_controle_base(r2)}`", inline=True)
    embed.add_field(name="Diferença", value=f"`{diff:,}`", inline=False)

    embed.add_field(
        name="🎯 CONTROLE",
        value=(f"**{k1}** usando técnica de controle contra **{k2}**: gasta `{custo_1v2}` ponto(s)\n"
               f"**{k2}** usando técnica de controle contra **{k1}**: gasta `{custo_2v1}` ponto(s)"),
        inline=False
    )
    embed.add_field(
        name="🌌 CONFLITO DE REINOS / DOMÍNIOS",
        value=avaliar_conflito_reinos(r1, r2, k1, k2),
        inline=False
    )
    embed.add_field(
        name=f"💥 IMPACTO ({mais_forte} sobre {mais_fraco})",
        value=avaliar_impacto_reiatsu(max(r1,r2), min(r1,r2), mais_forte, mais_fraco),
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="controle_gastar", description="Registra o uso de uma técnica de controle/manipulação")
@app_commands.describe(
    nome="Quem está usando a técnica",
    alvo="Alvo da técnica de controle"
)
async def controle_gastar(interaction, nome: str, alvo: str):
    data = load()
    key   = get_key(data, nome)
    key_a = get_key(data, alvo)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    if not key_a:
        await interaction.response.send_message(f"❌ **{alvo}** não encontrado.", ephemeral=True)
        return

    char   = data[key]
    char_a = data[key_a]
    r_atacante = char.get("reiatsu", 0)
    r_alvo     = char_a.get("reiatsu", 0)
    custo      = controle_gasto(r_atacante, r_alvo)
    antes      = char.get("controle", 3)

    if antes <= 0:
        await interaction.response.send_message(
            f"🔴 **{key}** está com controle negativo (`{antes}`). Técnicas de controle **falham automaticamente**.",
            embed=status_embed(key, char)
        )
        return

    char["controle"] = antes - custo
    save(data)

    if custo == 0:
        msg = (f"🟢 **{key}** usou técnica de controle contra **{key_a}**.\n"
               f"Diferença de Reiatsu é grande — **não gastou pontos de controle**.\n`Controle: {antes} → {char['controle']}`")
    else:
        msg = (f"🎯 **{key}** usou técnica de controle contra **{key_a}** "
               f"(custou `{custo}` ponto(s)).\n`Controle: {antes} → {char['controle']}`")
    if char["controle"] <= 0:
        msg += f"\n🔴 **{key}** chegou a controle negativo! Próximas técnicas de controle falham."

    await interaction.response.send_message(msg, embed=status_embed(key, char))

@tree.command(name="controle_set", description="Define manualmente os pontos de controle de um personagem")
@app_commands.describe(nome="Nome do personagem", valor="Novo valor de controle (pode ser negativo)")
async def controle_set(interaction, nome: str, valor: int):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    data[key]["controle"] = valor
    save(data)
    await interaction.response.send_message(
        f"🔮 **{key}** controle → `{valor}`",
        embed=status_embed(key, data[key])
    )

# ════════════════════════════════
# HADO DE APOSTA
# ════════════════════════════════

@tree.command(name="hado_aposta", description="Declara o Hado de Aposta — ambos ficam sem energia, inicia conflito de ringue")
@app_commands.describe(
    declarante="Quem está declarando o Hado de Aposta",
    oponente="Oponente que entra no ringue"
)
async def hado_aposta(interaction, declarante: str, oponente: str):
    data = load()
    k1 = get_key(data, declarante)
    k2 = get_key(data, oponente)
    if not k1:
        await interaction.response.send_message(f"❌ **{declarante}** não encontrado.", ephemeral=True)
        return
    if not k2:
        await interaction.response.send_message(f"❌ **{oponente}** não encontrado.", ephemeral=True)
        return

    c1 = data[k1]
    c2 = data[k2]

    en1_antes = c1["energia"]
    en2_antes = c2["energia"]

    c1["energia"] = 0
    c2["energia"] = 0

    save(data)

    embed = discord.Embed(
        title="⚡ HADO DE APOSTA DECLARADO",
        description=(
            f"**{k1}** declarou o Hado de Aposta contra **{k2}**.\n"
            f"Esta é uma declaração unilateral — **não pode ser recusada.**"
        ),
        color=0xe03060
    )
    embed.add_field(
        name="ENERGIA",
        value=(f"**{k1}**: `{en1_antes:,}` → `0` ☠️\n"
               f"**{k2}**: `{en2_antes:,}` → `0` ☠️"),
        inline=False
    )
    embed.add_field(
        name="REGRAS DO RINGUE",
        value=(
            "• Apenas artes marciais — nenhuma técnica especial permitida\n"
            "• Avaliado por IA com critérios objetivos: golpes acertados, qualidade, faltas\n"
            "• Mestre pode opinar mas não decide sozinho\n"
            "• Energia de ambos volta ao normal quando o ringue termina"
        ),
        inline=False
    )
    embed.add_field(
        name="RESULTADO (use /hado_resultado após o ringue)",
        value=(
            f"**Vencedor**: recupera 3 pontos de controle\n"
            f"**Perdedor**: perde 1 ponto de controle (pode negativar)"
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="hado_resultado", description="Aplica o resultado do Hado de Aposta e restaura a energia dos dois")
@app_commands.describe(
    vencedor="Nome do vencedor do ringue",
    perdedor="Nome do perdedor do ringue",
    energia_vencedor="Energia que o vencedor tinha antes do Hado",
    energia_perdedor="Energia que o perdedor tinha antes do Hado"
)
async def hado_resultado(interaction, vencedor: str, perdedor: str,
                          energia_vencedor: int, energia_perdedor: int):
    data = load()
    kv = get_key(data, vencedor)
    kp = get_key(data, perdedor)
    if not kv:
        await interaction.response.send_message(f"❌ **{vencedor}** não encontrado.", ephemeral=True)
        return
    if not kp:
        await interaction.response.send_message(f"❌ **{perdedor}** não encontrado.", ephemeral=True)
        return

    cv = data[kv]
    cp = data[kp]

    # Restaura energia
    cv["energia"] = min(cv["energia_max"], energia_vencedor)
    cp["energia"] = min(cp["energia_max"], energia_perdedor)

    # Controle do vencedor
    ctrl_v_antes = cv.get("controle", 3)
    ctrl_v_novo  = recuperar_controle_apos_aposta(ctrl_v_antes, ganhou=True)
    cv["controle"] = ctrl_v_novo

    # Controle do perdedor
    ctrl_p_antes = cp.get("controle", 3)
    ctrl_p_novo  = recuperar_controle_apos_aposta(ctrl_p_antes, ganhou=False)
    cp["controle"] = ctrl_p_novo

    save(data)

    embed = discord.Embed(title="🏆 RESULTADO DO HADO DE APOSTA", color=0xc8a020)
    embed.add_field(
        name=f"🏆 {kv} — VENCEDOR",
        value=(f"Controle: `{ctrl_v_antes}` → `{ctrl_v_novo}` (+recuperação)\n"
               f"Energia restaurada: `{cv['energia']:,}`"),
        inline=True
    )
    embed.add_field(
        name=f"💀 {kp} — PERDEDOR",
        value=(f"Controle: `{ctrl_p_antes}` → `{ctrl_p_novo}` (-1)\n"
               f"Energia restaurada: `{cp['energia']:,}`"),
        inline=True
    )

    alertas = []
    if ctrl_p_novo <= 0:
        alertas.append(f"🔴 **{kp}** está com controle negativo (`{ctrl_p_novo}`). "
                       f"Técnicas de controle falham. "
                       f"Recuperação no próximo Hado ganho: "
                       f"`{'2' if ctrl_p_novo == -1 else '1' if ctrl_p_novo == -2 else '0'}`")
    if alertas:
        embed.add_field(name="ALERTAS", value="\n".join(alertas), inline=False)

    await interaction.response.send_message(
        embed=embed
    )
    await interaction.followup.send(embed=status_embed(kv, cv))
    await interaction.followup.send(embed=status_embed(kp, cp))

# ════════════════════════════════
# STATS ESPECIAIS E ADMINISTRAÇÃO
# ════════════════════════════════

@tree.command(name="extra_set", description="Define um stat especial do personagem (ex: Queimadura, Corda)")
@app_commands.describe(
    nome="Nome do personagem",
    campo="Nome do stat especial",
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

@tree.command(name="extra_remover", description="Remove um stat especial de um personagem")
@app_commands.describe(nome="Nome do personagem", campo="Nome do stat a remover")
async def extra_remover(interaction, nome: str, campo: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    extras = data[key].get("extras", {})
    if campo not in extras:
        await interaction.response.send_message(f"❌ Stat `{campo}` não encontrado em **{key}**.", ephemeral=True)
        return
    del data[key]["extras"][campo]
    save(data)
    await interaction.response.send_message(f"🗑️ Stat `{campo}` removido de **{key}**.")

@tree.command(name="resetar", description="Reseta todos os stats de um personagem para o máximo base")
@app_commands.describe(nome="Nome do personagem")
async def resetar(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    char["hp"]        = char["hp_base"]
    char["hp_max"]    = char["hp_base"]
    char["energia"]   = char["energia_base"]
    char["energia_max"]= char["energia_base"]
    char["lba"]       = char["lba_base"]
    char["velocidade"]= char["velocidade_base"]
    char["evasivas"]  = 5
    char["controle"]  = char.get("controle_base", 3)
    char["estado"]    = "Base"
    save(data)
    await interaction.response.send_message(
        f"♻️ **{key}** totalmente resetado para o estado base.",
        embed=status_embed(key, char)
    )

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

# ════════════════════════════════
# AJUDA
# ════════════════════════════════

@tree.command(name="ajuda", description="Lista todos os comandos disponíveis")
async def ajuda(interaction):
    embed = discord.Embed(title="◈ FINAL DO VOID — BOT DE COMBATE", color=0xc8a020)
    embed.add_field(name="📋 PERSONAGENS", value=(
        "`/registrar` — cria personagem\n"
        "`/status [nome]` — status atual\n"
        "`/todos` — todos os personagens\n"
        "`/resetar [nome]` — reset total para a base\n"
        "`/deletar [nome]` — remove personagem"
    ), inline=False)
    embed.add_field(name="⚔️ COMBATE", value=(
        "`/dano [nome] [valor]` — aplica dano no HP\n"
        "`/curar [nome] [valor]` — cura HP\n"
        "`/gastar [nome] [valor]` — gasta energia\n"
        "`/recuperar [nome] [valor]` — recupera energia\n"
        "`/velocidade [nome] [1-10]` — altera velocidade\n"
        "`/lba [nome] [valor]` — altera LBA"
    ), inline=False)
    embed.add_field(name="💨 EVASIVAS", value=(
        "`/evasiva_usar [nome] [qtd]` — gasta evasivas\n"
        "`/evasiva_recuperar [nome]` — recupera base (5)\n"
        "`/evasiva_recuperar [nome] [oponente]` — recupera com bônus de velocidade\n"
        "`/comparar_velocidade [nome1] [nome2]` — compara velocidade e evasivas"
    ), inline=False)
    embed.add_field(name="✨ TRANSFORMAÇÕES", value=(
        "`/registrar_transformacao` — cadastra transformação *(sobre a base, nunca empilha)*\n"
        "`/transformar [nome] [estado]` — aplica transformação\n"
        "`/transformar [nome] base` — reverte para base\n"
        "`/listar_transformacoes [nome]` — lista todas\n"
        "`/deletar_transformacao [nome] [estado]` — remove transformação"
    ), inline=False)
    embed.add_field(name="🔮 REIATSU", value=(
        "`/comparar_reiatsu [nome1] [nome2]` — Controle, Reinos e Impacto\n"
        "`/controle_gastar [nome] [alvo]` — usa técnica de controle (desconta pontos)\n"
        "`/controle_set [nome] [valor]` — define controle manualmente"
    ), inline=False)
    embed.add_field(name="⚡ HADO DE APOSTA", value=(
        "`/hado_aposta [declarante] [oponente]` — declara o Hado (ambos ficam sem energia)\n"
        "`/hado_resultado [vencedor] [perdedor] [en_v] [en_p]` — aplica resultado e restaura energia"
    ), inline=False)
    embed.add_field(name="📌 STATS ESPECIAIS", value=(
        "`/extra_set [nome] [campo] [valor]` — define stat único\n"
        "`/extra_remover [nome] [campo]` — remove stat único"
    ), inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
PYEOF
echo "Feito — $(wc -l < /home/claude/bot.py) linhas"

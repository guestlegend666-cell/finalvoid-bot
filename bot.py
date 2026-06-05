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

# ── EVASIVAS: calcula bonus pela diferença de velocidade ──
def calcular_evasivas(vel_propria, vel_oponente):
    diff = vel_propria - vel_oponente
    base = 5
    if diff <= 0:
        return base
    elif diff <= 1:
        return base          # empate prático
    elif diff <= 3:
        return base + 2      # +2
    elif diff <= 5:
        return base + 4      # +4
    else:
        return base + 5      # +5

def evasivas_penalidade(vel_propria, vel_oponente):
    diff = vel_oponente - vel_propria
    if diff >= 6:
        return 3             # cai pra 3
    return 5                 # mantém base

# ── EMBED DE STATUS ──
def status_embed(name, char):
    estado = char.get("estado", "Base")
    cor = 0x4a7fff if estado == "Base" else 0x30d0c0

    hp_max = char.get("hp_max", char.get("hp", 0))
    en_max = char.get("energia_max", char.get("energia", 0))
    hp = char.get("hp", 0)
    en = char.get("energia", 0)
    hp_pct = int((hp / hp_max * 100)) if hp_max > 0 else 0
    en_pct = int((en / en_max * 100)) if en_max > 0 else 0

    vel = char.get("velocidade", 0)
    evasivas = char.get("evasivas", 5)

    def barra(pct):
        filled = int(pct / 10)
        return "█" * filled + "░" * (10 - filled) + f" {pct}%"

    def barra_evasivas(atual, maximo=10):
        filled = atual
        return "◆" * filled + "◇" * (maximo - filled) + f" {atual}"

    embed = discord.Embed(title=f"◈ {name}", color=cor)
    embed.add_field(name="Estado", value=f"`{estado}`", inline=True)
    embed.add_field(name="Reiatsu", value=f"`{char.get('reiatsu', '—'):,}`", inline=True)
    embed.add_field(name="Velocidade", value=f"`{vel}/10`", inline=True)
    embed.add_field(name=f"HP [{hp:,} / {hp_max:,}]", value=barra(hp_pct), inline=False)
    embed.add_field(name=f"Energia Amaldiçoada [{en:,} / {en_max:,}]", value=barra(en_pct), inline=False)
    embed.add_field(name="LBA", value=f"`{char.get('lba', '—'):,}`", inline=True)
    embed.add_field(name="Evasivas", value=barra_evasivas(evasivas), inline=True)

    extras = char.get("extras", {})
    if extras:
        for k, v in extras.items():
            embed.add_field(name=k, value=f"`{v}`", inline=True)

    alertas = []
    if hp_pct <= 20:
        alertas.append("⚠️ HP CRÍTICO")
    if en_pct <= 10:
        alertas.append("⚠️ ENERGIA CRÍTICA — IMINENTE INATIVO")
    if en <= 0:
        alertas.append("☠️ ENERGIA ZERADA — PERSONAGEM INATIVO")
    if evasivas == 0:
        alertas.append("💨 SEM EVASIVAS — RECUPERE COM TÉCNICA DE VELOCIDADE")
    if alertas:
        embed.add_field(name="ALERTAS", value="\n".join(alertas), inline=False)

    return embed

# ── SINCRONIZAR ──
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot online: {bot.user}")

# Comando para forçar sync no servidor (use uma vez após atualizar)
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

# ════════════════════════════════
# COMANDOS
# ════════════════════════════════

# /registrar
@tree.command(name="registrar", description="Registra um personagem no sistema")
@app_commands.describe(
    nome="Nome do personagem",
    hp="HP máximo",
    energia="Energia amaldiçoada máxima",
    reiatsu="Reiatsu (fixo, não muda em combate) — de 10.000 a 100.000",
    lba="LBA base",
    velocidade="Velocidade de 1 a 10"
)
async def registrar(interaction, nome: str, hp: int, energia: int, reiatsu: int, lba: int, velocidade: app_commands.Range[int, 1, 10]):
    data = load()
    data[nome] = {
        "hp": hp, "hp_max": hp,
        "energia": energia, "energia_max": energia,
        "reiatsu": reiatsu,
        "lba": lba, "lba_base": lba,
        "velocidade": velocidade, "velocidade_base": velocidade,
        "evasivas": 5,
        "estado": "Base",
        "transformacoes": {},
        "extras": {}
    }
    save(data)
    await interaction.response.send_message(f"✅ **{nome}** registrado!", embed=status_embed(nome, data[nome]))

# /status
@tree.command(name="status", description="Mostra o status atual de um personagem")
@app_commands.describe(nome="Nome do personagem")
async def status(interaction, nome: str):
    data = load()
    char = get_char(data, nome)
    if not char:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    await interaction.response.send_message(embed=status_embed(nome, char))

# /todos
@tree.command(name="todos", description="Mostra o status de todos os personagens")
async def todos(interaction):
    data = load()
    if not data:
        await interaction.response.send_message("Nenhum personagem registrado ainda.")
        return
    await interaction.response.defer()
    for nome, char in data.items():
        await interaction.followup.send(embed=status_embed(nome, char))

# /dano
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

# /curar
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

# /gastar
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

# /recuperar
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

# /velocidade
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

# /evasiva_usar
@tree.command(name="evasiva_usar", description="Registra o uso de evasivas em um desvio")
@app_commands.describe(
    nome="Nome do personagem",
    quantidade="Quantas evasivas foram gastas"
)
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
            f"❌ **{key}** não tem evasivas restantes. Use `/evasiva_recuperar` com sua técnica de velocidade.",
            ephemeral=True
        )
        return
    char["evasivas"] = max(0, antes - quantidade)
    save(data)
    msg = f"💨 **{key}** usou `{quantidade}` evasiva(s).\n`Evasivas: {antes} → {char['evasivas']}`"
    if char["evasivas"] == 0:
        msg += "\n💨 **SEM EVASIVAS — RECUPERE COM TÉCNICA DE VELOCIDADE**"
    await interaction.response.send_message(msg, embed=status_embed(key, char))

# /evasiva_recuperar — restaura para 5 base
@tree.command(name="evasiva_recuperar", description="Recupera as evasivas de um personagem para o padrão base (5)")
@app_commands.describe(nome="Nome do personagem")
async def evasiva_recuperar(interaction, nome: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]
    char["evasivas"] = 5
    save(data)
    await interaction.response.send_message(
        f"💨 **{key}** recuperou evasivas.\nRestaurado para o padrão base (5)\n`Evasivas: 5`",
        embed=status_embed(key, char)
    )

# /comparar_velocidade
@tree.command(name="comparar_velocidade", description="Mostra a diferença de velocidade e evasivas entre dois personagens")
@app_commands.describe(
    nome1="Primeiro personagem",
    nome2="Segundo personagem"
)
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

# /lba
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

# /registrar_transformacao
@tree.command(name="registrar_transformacao", description="Registra uma transformação para um personagem")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação (ex: Shikai, Bankai, Ressurreição)",
    hp_mult="Multiplicador de HP (ex: 1.5 = +50%). Use 1 pra não mudar.",
    energia_mult="Multiplicador de Energia. Use 1 pra não mudar.",
    lba_mult="Multiplicador de LBA. Use 1 pra não mudar.",
    vel_add="Pontos de velocidade a adicionar (ex: 1 = +1 no número). Use 0 pra não mudar."
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

# /transformar
@tree.command(name="transformar", description="Aplica uma transformação no personagem (multiplica stats atuais)")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação (ou 'base' para reverter)"
)
async def transformar(interaction, nome: str, estado: str):
    data = load()
    key = get_key(data, nome)
    if not key:
        await interaction.response.send_message(f"❌ **{nome}** não encontrado.", ephemeral=True)
        return
    char = data[key]

    if estado.lower() == "base":
        char["estado"] = "Base"
        char["lba"] = char.get("lba_base", char["lba"])
        char["velocidade"] = char.get("velocidade_base", char["velocidade"])
        save(data)
        await interaction.response.send_message(
            f"🔄 **{key}** reverteu para **Base**.",
            embed=status_embed(key, char)
        )
        return

    transformacoes = char.get("transformacoes", {})
    t = transformacoes.get(estado.lower())
    if not t:
        await interaction.response.send_message(
            f"❌ Transformação **{estado}** não registrada para **{key}**.\n"
            f"Use `/registrar_transformacao` primeiro.",
            ephemeral=True
        )
        return

    char["hp"] = int(char["hp"] * t["hp_mult"])
    char["hp_max"] = int(char["hp_max"] * t["hp_mult"])
    char["energia"] = int(char["energia"] * t["energia_mult"])
    char["energia_max"] = int(char["energia_max"] * t["energia_mult"])
    char["lba"] = int(char["lba"] * t["lba_mult"])
    char["velocidade"] = min(10, char["velocidade"] + t.get("vel_add", 0))
    char["estado"] = t["nome"]

    save(data)
    await interaction.response.send_message(
        f"✨ **{key}** entrou em **{t['nome']}**!",
        embed=status_embed(key, char)
    )

# /deletar_transformacao
@tree.command(name="deletar_transformacao", description="Remove uma transformação registrada de um personagem")
@app_commands.describe(
    nome="Nome do personagem",
    estado="Nome da transformação a deletar (ex: Shikai)"
)
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
            f"❌ Transformação **{estado}** não encontrada em **{key}**.\nTransformações registradas: {lista}",
            ephemeral=True
        )
        return
    nome_real = transformacoes[t_key]["nome"]
    del data[key]["transformacoes"][t_key]
    save(data)
    await interaction.response.send_message(
        f"🗑️ Transformação **{nome_real}** removida de **{key}**."
    )

# /listar_transformacoes
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
    await interaction.response.send_message(embed=embed)

# /extra_set
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

# /resetar
@tree.command(name="resetar", description="Reseta todos os stats de um personagem para o máximo")
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
    char["lba"] = char.get("lba_base", char["lba"])
    char["velocidade"] = char.get("velocidade_base", char["velocidade"])
    char["evasivas"] = 5
    char["estado"] = "Base"
    save(data)
    await interaction.response.send_message(
        f"♻️ **{key}** resetado para o estado base.",
        embed=status_embed(key, char)
    )

# /deletar
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

# /ajuda
@tree.command(name="ajuda", description="Lista todos os comandos disponíveis")
async def ajuda(interaction):
    embed = discord.Embed(title="◈ FINAL DO VOID — BOT DE COMBATE", color=0x4a7fff)
    embed.add_field(name="📋 PERSONAGENS", value=
        "`/registrar` — cria personagem com stats base\n"
        "`/status [nome]` — mostra status atual\n"
        "`/todos` — mostra todos os personagens\n"
        "`/resetar [nome]` — reseta HP, energia, evasivas e velocidade\n"
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
        "`/evasiva_usar [nome] [qtd]` — registra evasivas gastas\n"
        "`/evasiva_recuperar [nome]` — recupera evasivas base (5)\n"
        "`/evasiva_recuperar [nome] [oponente]` — recupera com bônus de velocidade\n"
        "`/comparar_velocidade [nome1] [nome2]` — mostra diferença e evasivas de cada um",
        inline=False)
    embed.add_field(name="✨ TRANSFORMAÇÕES", value=
        "`/registrar_transformacao` — cadastra transformação com multiplicadores\n"
        "`/transformar [nome] [estado]` — aplica transformação nos stats atuais\n"
        "`/transformar [nome] base` — reverte para base\n"
        "`/listar_transformacoes [nome]` — lista todas as transformações\n"
        "`/deletar_transformacao [nome] [estado]` — remove uma transformação",
        inline=False)
    embed.add_field(name="📌 STATS ESPECIAIS", value=
        "`/extra_set [nome] [campo] [valor]` — define stat único\n"
        "Ex: `/extra_set Halo Queimadura 50%`\n"
        "Ex: `/extra_set Tamsy Corda 70%`",
        inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)

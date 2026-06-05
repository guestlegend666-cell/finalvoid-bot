# FINAL DO VOID — BOT DE COMBATE
## GUIA DE INSTALAÇÃO COMPLETO

---

## PASSO 1 — CRIAR O BOT NO DISCORD

1. Acesse https://discord.com/developers/applications
2. Clique em **"New Application"**
3. Dê o nome que quiser (ex: "FinalVoidBot")
4. No menu lateral, clique em **"Bot"**
5. Clique em **"Add Bot"** → confirma
6. Em **"TOKEN"**, clique em **"Reset Token"** e copie o token
   ⚠️ GUARDE ESSE TOKEN — você vai precisar dele depois
7. Ative as três opções abaixo:
   - ✅ PRESENCE INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT

---

## PASSO 2 — ADICIONAR O BOT AO SERVIDOR

1. No menu lateral, clique em **"OAuth2"** → **"URL Generator"**
2. Em SCOPES, marque: `bot` e `applications.commands`
3. Em BOT PERMISSIONS, marque:
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
4. Copie a URL gerada no final e abra no navegador
5. Selecione seu servidor do RP e confirme

---

## PASSO 3 — SUBIR O CÓDIGO NO GITHUB

1. Acesse https://github.com e crie uma conta se não tiver
2. Clique em **"New repository"**
3. Nome: `finalvoid-bot` | Deixe **privado**
4. Clique em **"Create repository"**
5. Na tela seguinte, clique em **"uploading an existing file"**
6. Faça upload dos 3 arquivos:
   - `bot.py`
   - `requirements.txt`
   - `railway.toml`
7. Clique em **"Commit changes"**

---

## PASSO 4 — HOSPEDAR NO RAILWAY (GRÁTIS)

1. Acesse https://railway.app
2. Clique em **"Login"** → entre com sua conta do GitHub
3. Clique em **"New Project"**
4. Selecione **"Deploy from GitHub repo"**
5. Selecione o repositório `finalvoid-bot`
6. O Railway vai detectar o código automaticamente

---

## PASSO 5 — CONFIGURAR O TOKEN

1. Dentro do projeto no Railway, clique na aba **"Variables"**
2. Clique em **"New Variable"**
3. Nome: `DISCORD_TOKEN`
4. Valor: cole o token que você copiou no Passo 1
5. Clique em **"Add"**
6. O Railway vai reiniciar o bot automaticamente

---

## PASSO 6 — VERIFICAR SE ESTÁ FUNCIONANDO

1. No Railway, clique na aba **"Deployments"**
2. Deve aparecer um deploy com status **"Success"** (verde)
3. No Discord, o bot deve aparecer como online no servidor
4. Digite `/ajuda` em qualquer canal — deve aparecer a lista de comandos

---

## COMANDOS — REFERÊNCIA RÁPIDA

### Registrar personagem
```
/registrar nome:Halo hp:50000 energia:990000 reiatsu:35000 lba:5000 velocidade:60
```

### Ver status
```
/status nome:Halo
/todos
```

### Combate
```
/dano nome:Halo valor:5000
/curar nome:Halo valor:3000
/gastar nome:Halo valor:10000
/recuperar nome:Halo valor:5000
/velocidade nome:Halo valor:80
/lba nome:Halo valor:7000
```

### Transformações
```
# Registrar (só precisa fazer uma vez)
/registrar_transformacao nome:Halo estado:Shikai hp_mult:1 energia_mult:1 lba_mult:1.4 vel_mult:1

# Aplicar (aplica nos stats ATUAIS, não no máximo)
/transformar nome:Halo estado:Shikai

# Reverter
/transformar nome:Halo estado:base
```

### Stats especiais (Queimadura, Corda etc)
```
/extra_set nome:Halo campo:Queimadura valor:50%
/extra_set nome:Tamsy campo:Corda valor:70%
```

### Resetar / Remover
```
/resetar nome:Halo
/deletar nome:Halo
```

---

## PROBLEMAS COMUNS

**Bot aparece offline:**
- Verifique se o TOKEN está correto nas Variables do Railway
- Verifique se os Intents estão ativados no Discord Developer Portal

**Comandos não aparecem:**
- Aguarde até 1 hora — o Discord demora pra sincronizar slash commands
- Ou remova e adicione o bot ao servidor novamente

**Erro no deploy:**
- Verifique se os 3 arquivos foram enviados corretamente ao GitHub
- O arquivo `requirements.txt` precisa estar na raiz do repositório

---

## PLANO GRATUITO DO RAILWAY

O Railway oferece $5 de crédito por mês gratuitamente.
Um bot simples como esse gasta em torno de $0.50-1.00 por mês.
Ou seja: funciona de graça sem precisar colocar cartão.

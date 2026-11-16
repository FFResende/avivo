import streamlit as st
import streamlit.components.v1 as components
import json
import os
from datetime import datetime, timedelta
import calendar
import hashlib
import re

# Configuração da página
st.set_page_config(
    page_title="Calendario de Revisao Espacada",
    page_icon="🩺",
    layout="wide"
)

DIRETORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
ARQUIVO_USUARIOS = os.path.join(DIRETORIO_SCRIPT, "usuarios_sistema.json")

def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS):
        try:
            with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if not conteudo:
                    return {}
                return json.loads(conteudo)
        except:
            return {}
    return {}

def salvar_usuarios(usuarios):
    with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=4)

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# --- SISTEMA DE AUTENTICAÇÃO E SESSÃO ---
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def tela_autenticacao():
    st.markdown("""
        <div style="text-align: center; padding: 30px 0;">
            <h1 style="color: #0d9488; font-size: 32px;">🩺 Planejador Médico & Revisão Espaçada</h1>
            <p style="color: #64748b; font-size: 16px;">Faça login na sua conta ou cadastre-se para acessar seu painel privado.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        aba_login, aba_cadastro = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
        
        usuarios = carregar_usuarios()
        
        with aba_login:
            st.markdown("### Acessar Painel")
            with st.form("form_login"):
                user_input = st.text_input("Usuário:")
                senha_input = st.text_input("Senha:", type="password")
                
                submitted_login = st.form_submit_button("🚀 Entrar no Sistema", use_container_width=True)
                if submitted_login:
                    if user_input in usuarios and usuarios[user_input]["senha"] == hash_senha(senha_input):
                        st.session_state["usuario_logado"] = user_input
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                    
        with aba_cadastro:
            st.markdown("### Novo Cadastro")
            with st.form("form_cadastro"):
                novo_user = st.text_input("Escolha um Usuário:")
                nova_senha = st.text_input("Escolha uma Senha:", type="password")
                confirma_senha = st.text_input("Confirme a Senha:", type="password")
                
                submitted_cad = st.form_submit_button("✨ Cadastrar Conta", use_container_width=True)
                if submitted_cad:
                    if not novo_user.strip() or not nova_senha.strip() or not confirma_senha.strip():
                        st.warning("Preencha todos os campos.")
                    elif novo_user in usuarios:
                        st.error("Este nome de usuário já existe. Escolha outro.")
                    elif nova_senha != confirma_senha:
                        st.error("As senhas não coincidem.")
                    else:
                        usuarios[novo_user] = {
                            "senha": hash_senha(nova_senha)
                        }
                        salvar_usuarios(usuarios)
                        st.success("Conta criada com sucesso! Vá para a aba 'Entrar' para fazer o login.")

# Se não estiver logado, exibe apenas a tela de login/cadastro
if not st.session_state["usuario_logado"]:
    tela_autenticacao()
    st.stop()

# --- SE ESTIVER LOGADO, CARREGA OS DADOS ESPECÍFICOS DO USUÁRIO ---
usuario_atual = st.session_state["usuario_logado"]
ARQUIVO_DADOS = os.path.join(DIRETORIO_SCRIPT, f"estudos_calendario_{usuario_atual}.json")
ARQUIVO_CONFIG = os.path.join(DIRETORIO_SCRIPT, f"config_horarios_{usuario_atual}.json")

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if not conteudo:
                    return []
                return json.loads(conteudo)
        except:
            return []
    return []

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

def carregar_config():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if not conteudo:
                    return {"sono_inicio": 23, "sono_fim": 7, "aulas": []}
                return json.loads(conteudo)
        except:
            return {"sono_inicio": 23, "sono_fim": 7, "aulas": []}
    return {"sono_inicio": 23, "sono_fim": 7, "aulas": []}

def salvar_config(config):
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def gerar_cronograma_anual(data_inicio):
    datas = []
    datas.append(data_inicio.strftime("%Y-%m-%d"))
    prox = data_inicio + timedelta(days=7)
    limite = data_inicio + timedelta(days=365)
    
    while prox <= limite:
        datas.append(prox.strftime("%Y-%m-%d"))
        prox += timedelta(days=15)
    return datas

def obter_horario_revisao(item, data_str):
    horarios_esp = item.get("horarios_especificos", {})
    if data_str in horarios_esp:
        return horarios_esp[data_str]
    return item.get("horario_fixo", "15:00")

def gerar_lista_horarios_brutos():
    horarios = []
    for hora in range(24):
        for minuto in range(0, 60, 10):
            horarios.append(f"{hora:02d}:{minuto:02d}")
    return horarios

def gerar_lista_horarios(config, dados, data_alvo_str, ignorar_item_id=None):
    sono_ini = config.get("sono_inicio", 23)
    sono_fim = config.get("sono_fim", 7)
    
    ocupados = {}
    for item in dados:
        if ignorar_item_id is not None and item.get("id") == ignorar_item_id:
            continue
        if data_alvo_str in item.get("revisoes", []):
            h = obter_horario_revisao(item, data_alvo_str)
            if h:
                mat = item.get("materia", "Geral")
                tit = item.get("titulo", "Estudo")
                ocupados[h] = f"{mat} - {tit}"
                
    opcoes_visuais = []
    mapa_real = {}
    
    for hora in range(24):
        if sono_ini > sono_fim:
            if hora >= sono_ini or hora < sono_fim:
                continue
        else:
            if sono_ini <= hora < sono_fim:
                continue
                
        for minuto in range(0, 60, 10):
            h_str = f"{hora:02d}:{minuto:02d}"
            if h_str in ocupados:
                label = f"{h_str} ⚠️ (Ocupado: {ocupados[h_str]})"
            else:
                label = f"{h_str} 🟢 (Livre)"
            opcoes_visuais.append(label)
            mapa_real[label] = h_str
            
    return opcoes_visuais, mapa_real

def parse_tempo_em_minutos(tempo_str):
    if not tempo_str:
        return 30
    total = 0
    if "hora" in tempo_str:
        if "1 hora" in tempo_str:
            total += 60
        elif "2 hora" in tempo_str:
            total += 120
        elif "3 hora" in tempo_str:
            total += 180
    if "minuto" in tempo_str:
        nums = re.findall(r'\d+', tempo_str)
        if "hora" in tempo_str and len(nums) > 1:
            total += int(nums[1])
        elif "hora" not in tempo_str and len(nums) > 0:
            total = int(nums[0])
    return total if total > 0 else 30

def render_timer_html(timer_id, duration_minutes, title_label):
    seconds = duration_minutes * 60
    html_code = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #334155; max-width: 320px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 13px; color: #38bdf8; margin-bottom: 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">⏱️ {title_label}</div>
        <div id="timer-{timer_id}" style="font-size: 38px; font-weight: bold; color: #ffffff; margin: 8px 0; text-align: center; letter-spacing: 2px;">{duration_minutes:02d}:00</div>
        <div id="status-{timer_id}" style="font-size: 12px; color: #94a3b8; margin-bottom: 12px; text-align: center;">Pronto para iniciar</div>
        <div style="display: flex; gap: 8px; justify-content: center;">
            <button onclick="startTimer_{timer_id}()" style="background: #0d9488; color: white; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; transition: 0.2s;">▶️ Iniciar</button>
            <button onclick="pauseTimer_{timer_id}()" style="background: #d97706; color: white; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; transition: 0.2s;">⏸️ Pausar</button>
            <button onclick="resetTimer_{timer_id}()" style="background: #475569; color: white; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; transition: 0.2s;">🔄 Resetar</button>
        </div>
    </div>
    
    <script>
        let totalSeconds_{timer_id} = {seconds};
        let timerInterval_{timer_id} = null;
        let remaining_{timer_id} = totalSeconds_{timer_id};

        function updateDisplay_{timer_id}() {{
            let m = Math.floor(remaining_{timer_id} / 60);
            let s = remaining_{timer_id} % 60;
            document.getElementById('timer-{timer_id}').innerText = 
                (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }}

        function startTimer_{timer_id}() {{
            if (timerInterval_{timer_id}) return;
            document.getElementById('status-{timer_id}').innerText = '🔥 Foco total em andamento...';
            timerInterval_{timer_id} = setInterval(() => {{
                if (remaining_{timer_id} > 0) {{
                    remaining_{timer_id}--;
                    updateDisplay_{timer_id}();
                }} else {{
                    clearInterval(timerInterval_{timer_id});
                    timerInterval_{timer_id} = null;
                    document.getElementById('timer-{timer_id}').innerText = '00:00';
                    document.getElementById('status-{timer_id}').innerHTML = '<span style="color: #4ade80; font-weight: bold; font-size: 13px;">🎉 Parabéns! Ciclo concluído com sucesso!</span>';
                    let audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
                    audio.play().catch(e => console.log(e));
                }}
            }}, 1000);
        }}

        function pauseTimer_{timer_id}() {{
            clearInterval(timerInterval_{timer_id});
            timerInterval_{timer_id} = null;
            document.getElementById('status-{timer_id}').innerText = '⏸️ Pausado';
        }}

        function resetTimer_{timer_id}() {{
            clearInterval(timerInterval_{timer_id});
            timerInterval_{timer_id} = null;
            remaining_{timer_id} = totalSeconds_{timer_id};
            updateDisplay_{timer_id}();
            document.getElementById('status-{timer_id}').innerText = 'Pronto para iniciar';
        }}
    </script>
    """
    components.html(html_code, height=175)

# --- CABEÇALHO DO PAINEL COM BOTÃO DE SAIR ---
col_head1, col_head2 = st.columns([5, 1])
with col_head1:
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 12px; border: 1px solid #334155; color: white; margin-bottom: 20px;">
            <h1 style="color: white !important; margin: 0; font-size: 26px;">Planejador Médico & Revisão Espaçada</h1>
            <p style="color: #94a3b8 !important; margin: 0; font-size: 14px;">Bem-vindo(a), <b>{usuario_atual}</b>! • Rumo à excelência médica.</p>
        </div>
    """, unsafe_allow_html=True)
with col_head2:
    st.write("")
    if st.button("🚪 Sair / Logout"):
        st.session_state["usuario_logado"] = None
        st.rerun()

dados = carregar_dados()
config = carregar_config()
hoje = datetime.now().date()
hoje_str = hoje.strftime("%Y-%m-%d")

# Barra lateral para cadastrar novo tópico
st.sidebar.header("➕ Adicionar Novo Tópico")

materias_cadastradas = [a["materia"] for a in config.get("aulas", [])]
if not materias_cadastradas:
    materias_disponiveis = ["Geral (Cadastre matérias na aba Grade)"]
else:
    materias_disponiveis = materias_cadastradas

materia_escolhida = st.sidebar.selectbox("📖 Selecione a Matéria:", materias_disponiveis)
novo_titulo = st.sidebar.text_input("📝 Título do Tópico (ex: Rim, Glúteo, Cardio)")

opcoes_tempo = [
    "10 minutos", "20 minutos", "30 minutos", "40 minutos", "50 minutos",
    "1 hora", "1 hora e 10 minutos", "1 hora e 20 minutos", "1 hora e 30 minutos"
]
tempo_estudo = st.sidebar.selectbox("⏱️ Tempo necessário:", opcoes_tempo)

opcoes_horarios, mapa_horarios = gerar_lista_horarios(config, dados, hoje_str)

idx_padrao = 0
for i, op in enumerate(opcoes_horarios):
    if op.startswith("15:00"):
        idx_padrao = i
        break

horario_selecionado_label = st.sidebar.selectbox(
    "🕒 Escolha o Horário:", 
    opcoes_horarios, 
    index=idx_padrao
)
horario_escolhido = mapa_horarios[horario_selecionado_label]

if st.sidebar.button("🚀 Cadastrar Tópico e Gerar Ciclo"):
    if not materias_cadastradas:
        st.sidebar.error("⚠️ Cadastre pelo menos uma matéria na aba '🏫 Grade de Aulas e Sono' primeiro!")
    elif novo_titulo.strip():
        cronograma = gerar_cronograma_anual(hoje)
        
        conflito = False
        for item in dados:
            if hoje_str in item.get("revisoes", []) and obter_horario_revisao(item, hoje_str) == horario_escolhido:
                conflito = True
                break
        
        if conflito:
            st.sidebar.error(f"⚠️ O horário {horario_escolhido} já está ocupado hoje! Selecione um horário '🟢 (Livre)' na lista acima.")
        else:
            ids_existentes = [item.get("id", i) for i, item in enumerate(dados)]
            novo_id = max(ids_existentes, default=0) + 1
            novo_item = {
                "id": novo_id,
                "materia": materia_escolhida,
                "titulo": novo_titulo.strip(),
                "tempo_necessario": tempo_estudo,
                "horario_fixo": horario_escolhido,
                "horarios_especificos": {},
                "data_cadastro": hoje_str,
                "revisoes": cronograma,
                "indice_atual": 0
            }
            dados.append(novo_item)
            salvar_dados(dados)
            st.sidebar.success(f"Tópico '{novo_titulo}' cadastrado com sucesso!")
            st.rerun()
    else:
        st.sidebar.error("Digite um título válido.")

# Abas de navegacao
aba1, aba2, aba3, aba4 = st.tabs([
    "⭐ Revisões de Hoje", 
    "📅 Calendário e Reagendamento", 
    "🏫 Grade de Aulas e Sono", 
    "📊 Dashboard & Estatísticas"
])

with aba1:
    st.subheader(f"✨ Revisões Pendentes para Hoje ({hoje.strftime('%d/%m/%Y')})")
    
    atrasadas = []
    de_hoje = []
    
    for item in dados:
        indice = item.get("indice_atual", 0)
        revisoes = item.get("revisoes", [])
        if indice < len(revisoes):
            data_rev = revisoes[indice]
            if data_rev < hoje_str:
                atrasadas.append((item, data_rev, indice))
            elif data_rev == hoje_str:
                de_hoje.append((item, data_rev, indice))

    # Exibição de Atrasadas se houver
    if atrasadas:
        st.warning(f"⚠️ Você tem **{len(atrasadas)} revisão(ões) atrasada(s)** de dias anteriores!")
        atrasadas.sort(key=lambda x: obter_horario_revisao(x[0], x[1]))
        for item, data_rev, indice in atrasadas:
            data_fmt = datetime.strptime(data_rev, "%Y-%m-%d").strftime("%d/%m/%Y")
            duracao = item.get("tempo_necessario", "30 minutos")
            horario = obter_horario_revisao(item, data_rev)
            mat_nome = item.get("materia", "Geral")
            tit_nome = item.get("titulo", "Estudo")
            item_id = item.get("id", indice)
            
            with st.container():
                st.markdown(f"🔴 **[ATRASADA] [{mat_nome}] {tit_nome}** | Data original: {data_fmt} | 🕒 **{horario}** ({duracao})")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    if st.button("✅ Concluir Atrasada", key=f"concluir_atrasada_{item_id}_{data_rev}"):
                        item["indice_atual"] = indice + 1
                        salvar_dados(dados)
                        st.success("Revisão concluída!")
                        st.rerun()
                with col_a2:
                    if st.button("🔄 Trazer para Hoje", key=f"trazer_hoje_{item_id}_{data_rev}"):
                        horarios_esp = item.get("horarios_especificos", {})
                        if data_rev in horarios_esp:
                            horarios_esp[hoje_str] = horarios_esp.pop(data_rev)
                            item["horarios_especificos"] = horarios_esp
                        item["revisoes"][indice] = hoje_str
                        salvar_dados(dados)
                        st.warning("Revisão remarcada para hoje!")
                        st.rerun()
                st.markdown("---")

    # Exibição de Hoje
    if not de_hoje and not atrasadas:
        st.success("🎉 Nenhuma revisão pendente para hoje. Excelente trabalho doutor(a)!")
    elif de_hoje:
        de_hoje.sort(key=lambda x: obter_horario_revisao(x[0], x[1]))
        for item, data_rev, indice in de_hoje:
            duracao_str = item.get("tempo_necessario", "30 minutos")
            minutos_totais = parse_tempo_em_minutos(duracao_str)
            horario = obter_horario_revisao(item, data_rev)
            mat_nome = item.get("materia", "Geral")
            tit_nome = item.get("titulo", "Estudo")
            item_id = item.get("id", indice)
            
            st.markdown(f"### 📌 **[{mat_nome}] {tit_nome}**")
            st.markdown(f"🕒 **Horário:** `{horario}` | ⏳ **Duração:** *{duracao_str}*")
            
            if minutos_totais < 60:
                titulo_timer = f"Foco Total ({duracao_str})"
                tempo_timer = minutos_totais
            else:
                titulo_timer = "Ciclo Pomodoro (25 min de foco)"
                tempo_timer = 25

            with st.expander(f"⏱️ Abrir Cronômetro ({titulo_timer})"):
                render_timer_html(f"{item_id}_{indice}", tempo_timer, titulo_timer)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Concluir Revisão", key=f"concluir_{item_id}_{data_rev}"):
                    item["indice_atual"] = indice + 1
                    salvar_dados(dados)
                    st.success(f"Revisão de '{tit_nome}' concluída!")
                    st.rerun()
            with col2:
                if st.button("🔄 Adiar para Amanhã", key=f"adiar_{item_id}_{data_rev}"):
                    amanha = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
                    horarios_esp = item.get("horarios_especificos", {})
                    if data_rev in horarios_esp:
                        horarios_esp[amanha] = horarios_esp.pop(data_rev)
                        item["horarios_especificos"] = horarios_esp
                    item["revisoes"][indice] = amanha
                    salvar_dados(dados)
                    st.warning("Revisão adiada para amanhã!")
                    st.rerun()
            st.markdown("---")

with aba2:
    st.subheader("📅 Calendário Anual (Visão Mensal)")
    st.markdown("Acompanhe seus compromissos mês a mês ou reorganize horários abaixo.")

    if not dados:
        st.info("Nenhum conteúdo cadastrado ainda.")
    else:
        eventos_por_data = {}
        for item in dados:
            for idx, rev in enumerate(item.get("revisoes", [])):
                status = "✅" if idx < item.get("indice_atual", 0) else "⏳"
                horario = obter_horario_revisao(item, rev)
                mat_nome = item.get("materia", "Geral")
                tit_nome = item.get("titulo", "Estudo")
                if rev not in eventos_por_data:
                    eventos_por_data[rev] = []
                eventos_por_data[rev].append((horario, f"{horario} - [{mat_nome}] {tit_nome} {status}"))

        for rev in eventos_por_data:
            eventos_por_data[rev].sort(key=lambda x: x[0])
            eventos_por_data[rev] = [x[1] for x in eventos_por_data[rev]]

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            mes_sel = st.selectbox("Mês:", list(range(1, 13)), index=hoje.month - 1, format_func=lambda x: datetime(2026, x, 1).strftime('%B'))
        with col_m2:
            ano_sel = st.selectbox("Ano:", [2026, 2027])

        st.markdown("---")

        cal = calendar.monthcalendar(ano_sel, mes_sel)
        dias_da_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        cols = st.columns(7)
        for i, dia_nome in enumerate(dias_da_semana):
            cols[i].markdown(f"**{dia_nome}**")

        for semana in cal:
            cols_semana = st.columns(7)
            for i, dia in enumerate(semana):
                with cols_semana[i]:
                    if dia == 0:
                        st.write("")
                    else:
                        data_atual_str = f"{ano_sel}-{mes_sel:02d}-{dia:02d}"
                        st.markdown(f"**{dia}**")
                        if data_atual_str in eventos_por_data:
                            for ev in eventos_por_data[data_atual_str]:
                                st.caption(ev)
            st.markdown("")

        st.markdown("---")
        
        st.subheader("🔄 Reagendar Horário ou Data de Revisão")
        st.markdown("💡 *Dica:* Clique na caixa abaixo e digite diretamente (ex: `perna`, `anatomia`, `23/03`) para filtrar e encontrar o tópico na hora.")

        opcoes_temas = {}
        for item in dados:
            mat = item.get("materia", "Geral")
            tit = item.get("titulo", "Estudo")
            
            revisoes = item.get("revisoes", [])
            indice_atual = item.get("indice_atual", 0)
            
            for idx, rev in enumerate(revisoes):
                if idx >= indice_atual:
                    dt_fmt = datetime.strptime(rev, "%Y-%m-%d").strftime("%d/%m/%Y")
                    h_atual = obter_horario_revisao(item, rev)
                    
                    label_opcao = f"[{mat}] {tit} — Data: {dt_fmt} ({h_atual})"
                    opcoes_temas[label_opcao] = (item, idx, rev)

        if not opcoes_temas:
            st.info("Nenhuma revisão pendente encontrada para reagendar.")
        else:
            tema_escolhido_label = st.selectbox("1. Selecione ou pesquise a revisão:", list(opcoes_temas.keys()))
            item_sel, idx_alvo, data_antiga_str = opcoes_temas[tema_escolhido_label]

            tipo_alteracao = st.radio(
                "2. O que você deseja fazer?",
                [
                    "Alterar APENAS UMA data específica (Imprevisto / Consulta médica)",
                    "Alterar o horário de TODAS as revisões futuras (Mudança na grade)"
                ]
            )

            if tipo_alteracao.startswith("Alterar APENAS UMA"):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    nova_data_dt = st.date_input(
                        "3. Nova Data:",
                        value=datetime.strptime(data_antiga_str, "%Y-%m-%d").date()
                    )
                nova_data_str = nova_data_dt.strftime("%Y-%m-%d")
                
                with col_r2:
                    opcoes_h_esp, mapa_h_esp = gerar_lista_horarios(config, dados, nova_data_str, ignorar_item_id=item_sel.get("id"))
                    h_atual_alvo = obter_horario_revisao(item_sel, data_antiga_str)
                    idx_h = 0
                    for i, op in enumerate(opcoes_h_esp):
                        if op.startswith(h_atual_alvo):
                            idx_h = i
                            break
                    novo_h_label = st.selectbox("4. Novo Horário:", opcoes_h_esp, index=idx_h)
                    novo_h_str = mapa_h_esp[novo_h_label]
                
                if st.button("💾 Salvar Alteração Pontual"):
                    conflito_pontual = False
                    for outro in dados:
                        if outro.get("id") != item_sel.get("id"):
                            if nova_data_str in outro.get("revisoes", []) and obter_horario_revisao(outro, nova_data_str) == novo_h_str:
                                conflito_pontual = True
                                break
                    
                    if conflito_pontual:
                        st.error(f"⚠️ Conflito! Já existe outro estudo marcado às {novo_h_str} no dia {nova_data_dt.strftime('%d/%m/%Y')}.")
                    else:
                        if "horarios_especificos" not in item_sel:
                            item_sel["horarios_especificos"] = {}
                        
                        if data_antiga_str in item_sel["horarios_especificos"]:
                            del item_sel["horarios_especificos"][data_antiga_str]
                            
                        item_sel["revisoes"][idx_alvo] = nova_data_str
                        
                        if novo_h_str != item_sel.get("horario_fixo"):
                            item_sel["horarios_especificos"][nova_data_str] = novo_h_str
                        
                        salvar_dados(dados)
                        st.success("Revisão remarcada com sucesso!")
                        st.rerun()

            else:
                opcoes_h_geral, mapa_h_geral = gerar_lista_horarios(config, dados, hoje_str, ignorar_item_id=item_sel.get("id"))
                h_fixo_atual = item_sel.get("horario_fixo", "15:00")
                idx_hg = 0
                for i, op in enumerate(opcoes_h_geral):
                    if op.startswith(h_fixo_atual):
                        idx_hg = i
                        break
                
                novo_h_geral_label = st.selectbox("3. Novo horário fixo:", opcoes_h_geral, index=idx_hg)
                novo_h_geral_str = mapa_h_geral[novo_h_geral_label]
                
                if st.button("💾 Atualizar Todas as Revisões Futuras"):
                    item_sel["horario_fixo"] = novo_h_geral_str
                    salvar_dados(dados)
                    st.success("Horário atualizado com sucesso!")
                    st.rerun()

with aba3:
    st.subheader("🏫 Configuração de Sono e Matérias da Faculdade")
    
    st.markdown("### 🛌 Horário de Sono")
    c1, c2 = st.columns(2)
    with c1:
        sono_inicio = st.number_input("Dormir (0-23):", min_value=0, max_value=23, value=config.get("sono_inicio", 23))
    with c2:
        sono_fim = st.number_input("Acordar (0-23):", min_value=0, max_value=23, value=config.get("sono_fim", 7))
    
    if st.button("💾 Salvar Horário de Sono"):
        config["sono_inicio"] = int(sono_inicio)
        config["sono_fim"] = int(sono_fim)
        salvar_config(config)
        st.success("Horário de sono atualizado!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📖 Cadastrar Matérias")
    
    lista_horarios_brutos = gerar_lista_horarios_brutos()
    
    with st.form("form_aula"):
        materia_aula = st.text_input("Nome da Matéria (ex: Histologia, Anatomia, Cardiologia)")
        
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            hora_inicio_sel = st.selectbox("Início da Aula:", lista_horarios_brutos, index=48)
        with col_h2:
            hora_fim_sel = st.selectbox("Término da Aula:", lista_horarios_brutos, index=66)
            
        opcoes_duracao = [
            "Ano Inteiro", 
            "1 mês", "2 meses", "3 meses", "4 meses", 
            "5 meses", "6 meses", "7 meses", "8 meses", 
            "9 meses", "10 meses", "11 meses", "12 meses"
        ]
        duracao_aula = st.selectbox("Duração do Período:", opcoes_duracao)
        
        if st.form_submit_button("➕ Adicionar Matéria"):
            if materia_aula.strip():
                horario_formatado = f"{hora_inicio_sel} às {hora_fim_sel}"
                config["aulas"].append({
                    "id": len(config["aulas"]) + 1,
                    "materia": materia_aula.strip(),
                    "horario": horario_formatado,
                    "duracao": duracao_aula
                })
                salvar_config(config)
                st.success(f"Matéria '{materia_aula}' cadastrada com sucesso!")
                st.rerun()
            else:
                st.warning("Insira o nome da matéria.")

    st.markdown("### 📋 Matérias Já Cadastradas")
    if not config.get("aulas", []):
        st.info("Nenhuma matéria cadastrada ainda.")
    else:
        for aula in config.get("aulas", []):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"- **{aula['materia']}** | Horário: {aula['horario']} | Período: *{aula['duracao']}*")
            with col_b:
                if st.button("🗑️ Excluir", key=f"del_a_{aula['id']}"):
                    config["aulas"] = [a for a in config["aulas"] if a["id"] != aula["id"]]
                    salvar_config(config)
                    st.success("Matéria removida!")
                    st.rerun()

with aba4:
    st.subheader("📊 Dashboard, Estatísticas e Backup")
    
    total_topicos = len(dados)
    total_revisoes_feitas = sum(item.get("indice_atual", 0) for item in dados)
    total_revisoes_planejadas = sum(len(item.get("revisoes", [])) for item in dados)
    porcentagem_geral = int((total_revisoes_feitas / total_revisoes_planejadas) * 100) if total_revisoes_planejadas > 0 else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("📚 Tópicos Cadastrados", total_topicos)
    col_m2.metric("✅ Revisões Concluídas", total_revisoes_feitas)
    col_m3.metric("📈 Progresso Geral do Ciclo", f"{porcentagem_geral}%")

    st.markdown("---")
    st.markdown("### 💾 Backup e Segurança dos Dados")
    st.markdown("Baixe uma cópia de segurança do seu progresso ou limpe os dados se necessário.")
    
    if dados:
        json_str = json.dumps(dados, ensure_ascii=False, indent=4)
        st.download_button(
            label="📥 Baixar Backup dos Estudos (.json)",
            data=json_str,
            file_name=f"backup_estudos_{hoje_str}.json",
            mime="application/json"
        )

    st.markdown("---")
    st.markdown("### 📚 Detalhamento por Matérias")

    if not dados:
        st.info("Nenhum tópico cadastrado ainda.")
    else:
        materias_dict = {}
        for item in dados:
            mat = item.get("materia", "Geral")
            if mat not in materias_dict:
                materias_dict[mat] = []
            materias_dict[mat].append(item)

        for materia_nome, topicos in materias_dict.items():
            st.markdown(f"### 📖 Matéria: {materia_nome}")
            
            for item in topicos:
                indice = item.get("indice_atual", 0)
                revisoes = item.get("revisoes", [])
                total_revs = len(revisoes)
                progresso = min(indice / total_revs, 1.0) if total_revs > 0 else 0.0
                
                proxima_data = "Ciclo Concluído"
                if indice < total_revs:
                    dt_prox_str = revisoes[indice]
                    h_prox = obter_horario_revisao(item, dt_prox_str)
                    dt_prox_fmt = datetime.strptime(dt_prox_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                    proxima_data = f"{dt_prox_fmt} às {h_prox}"

                duracao = item.get("tempo_necessario", "30 minutos")
                tit_topico = item.get("titulo", "Tópico")
                item_id = item.get("id", 0)

                with st.expander(f"🔹 Tópico: {tit_topico} — Progresso: {indice}/{total_revs} ({int(progresso * 100)}%)"):
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.markdown(f"**Próxima Revisão:** {proxima_data}")
                        st.markdown(f"**Tempo Necessário:** {duracao}")
                    with col_d2:
                        st.markdown(f"**Horário Padrão:** {item.get('horario_fixo', '15:00')}")

                    st.progress(progresso)
                    
                    st.markdown("---")
                    st.markdown("##### 🗓️ Cronograma deste Tópico:")
                    for idx_r, rev_data in enumerate(revisoes):
                        status_emoji = "✅ Concluída" if idx_r < indice else "⏳ Pendente"
                        h_especifico = obter_horario_revisao(item, rev_data)
                        dt_r_fmt = datetime.strptime(rev_data, "%Y-%m-%d").strftime("%d/%m/%Y")
                        st.caption(f"• **{dt_r_fmt}** às {h_especifico} — *{status_emoji}*")

                    st.markdown("---")
                    if st.button(f"🗑️ Excluir Tópico '{tit_topico}'", key=f"del_topico_{item_id}"):
                        dados = [d for d in dados if d.get("id") != item_id]
                        salvar_dados(dados)
                        st.warning("Tópico removido!")
                        st.rerun()
            st.markdown("---")
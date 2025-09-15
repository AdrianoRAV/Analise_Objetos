
import streamlit as st
import pandas as pd
import numpy as np
import mysql.connector
from datetime import datetime, date, time, timedelta
import plotly.express as px
import re

st.set_page_config(layout="wide")
# -----------------------
# Conexão conforme solicitado
# -----------------------
def init_connection():
    return mysql.connector.connect(
        host="IP",
        user="",
        password="",
        database="sci"
    )


# Planos fixos (conforme seu pedido)
PLANO_PERMITIDOS = (
    "E1_CTCE_BHE_1_IMP_SAE_ENV_SDX_1_CID_SAB",
    "E1_CTCE_BHE_1_IMP_SAE_ENV_SDX_4_5_ENV_CID",
)


# -----------------------
# utilitários de tempo
# -----------------------
def parse_time(v):
    """Converte vários formatos para datetime.time ou None."""
    import pandas as pd
    if v is None or pd.isna(v):
        return None
    if isinstance(v, time):
        return v
    if isinstance(v, (pd.Timestamp, datetime)):
        try:
            return v.time()
        except Exception:
            return None
    if isinstance(v, (pd.Timedelta, timedelta)):
        try:
            total_seconds = v.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            return time(hours, minutes, seconds)
        except Exception:
            return None

    s = str(v).strip()
    if s == "" or s.lower() in ["nan", "null", "(null)", "(nll)", "none", "nat"]:
        return None

    s = re.sub(r'[\(\)\s]', '', s)

    for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S", "%H%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            pass

    return None


def leq_time(h, cutoff):
    """Retorna True se h <= cutoff (tratando None)."""
    if h is None or cutoff is None:
        return False
    return h <= cutoff


# -----------------------
# Carregar dados do banco
# -----------------------

@st.cache_data(show_spinner=False)
def load_data_for_date(selected_date: date):
    cnx = init_connection()
    data_str = selected_date.strftime("%Y-%m-%d")
    prev_date_str = (selected_date - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        q_obj = (
            "SELECT * FROM tb_dados_stes "
            "WHERE plano IN (%s, %s) AND (DATE(data_lanc) = %s OR DATE(data_lanc) = %s)"
        )
        df_obj = pd.read_sql(
            q_obj,
            cnx,
            params=(PLANO_PERMITIDOS[0], PLANO_PERMITIDOS[1], prev_date_str, data_str)
        )
    except Exception as e:
        st.error(f"Erro ao carregar objetos: {e}")
        # Fallback para carregamento sem filtro de data
        df_obj = pd.read_sql(
            "SELECT * FROM tb_dados_stes WHERE plano IN (%s, %s)",
            cnx,
            params=(PLANO_PERMITIDOS[0], PLANO_PERMITIDOS[1])
        )

    # Resto do código permanece igual...
    except Exception as e:
        st.error(f"Erro ao carregar objetos: {e}")
        df_obj = pd.read_sql(
            "SELECT * FROM tb_dados_stes WHERE plano IN (%s, %s)",
            cnx,
            params=(PLANO_PERMITIDOS[0], PLANO_PERMITIDOS[1])
        )
        if "data_lanc" in df_obj.columns:
            df_obj["data_lanc"] = pd.to_datetime(df_obj["data_lanc"], errors="coerce").dt.date
            df_obj = df_obj[df_obj["data_lanc"] == selected_date]

    try:
        df_mat = pd.read_sql("SELECT * FROM tbl_entrega_matutina", cnx)
    except Exception as e:
        st.error(f"Erro ao carregar setups: {e}")
        try:
            df_mat = pd.read_sql("SELECT * FROM tbl_entrada_matutina", cnx)
        except:
            st.error("Não foi possível encontrar a tabela de setups")
            df_mat = pd.DataFrame()

    cnx.close()

    if "cod_sro" not in df_obj.columns:
        if "sro" in df_obj.columns:
            df_obj["cod_sro"] = df_obj["sro"].astype(str)
        else:
            df_obj["cod_sro"] = ""

    hora_col_candidates = ["hora", "hora_lanc", "hora_lancamento"]
    hora_col = next((c for c in hora_col_candidates if c in df_obj.columns), None)
    if hora_col:
        df_obj["hora_obj"] = df_obj[hora_col].apply(parse_time)
    else:
        df_obj["hora_obj"] = None

    if "data_lanc" in df_obj.columns:
        try:
            df_obj["data_lanc"] = pd.to_datetime(df_obj["data_lanc"], errors="coerce").dt.date
        except Exception:
            pass

    df_obj["_cod_sro"] = df_obj["cod_sro"].astype(str).str.strip()

    if df_mat.empty:
        st.warning("Tabela de setups vazia")
        return df_obj, df_mat

    if "sro" in df_mat.columns:
        df_mat["_sro_key"] = df_mat["sro"].astype(str).str.strip()
        if "unidade_destino" in df_mat.columns:
            df_mat["direcao"] = df_mat["unidade_destino"].astype(str).str.strip()
        else:
            df_mat["direcao"] = df_mat["_sro_key"]
    elif "unidade_destino" in df_mat.columns:
        df_mat["_sro_key"] = df_mat["unidade_destino"].astype(str).str.strip()
        df_mat["direcao"] = df_mat["unidade_destino"].astype(str).str.strip()
    else:
        df_mat["_sro_key"] = df_mat.iloc[:, 0].astype(str).str.strip()
        df_mat["direcao"] = df_mat.iloc[:, 0].astype(str).str.strip()

    return df_obj, df_mat


def count_objects_until_setup(df_obj, df_mat, selected_directions, setup_number, selected_date):
    df_obj["_cod_sro"] = df_obj["_cod_sro"].astype(str).str.strip()
    df_mat["_sro_key"] = df_mat["_sro_key"].astype(str).str.strip()

    if selected_directions:
        df_mat_f = df_mat[df_mat["direcao"].isin(selected_directions)].copy()
    else:
        df_mat_f = df_mat.copy()

    rows = []
    matches = []

    for idx, r in df_mat_f.iterrows():
        sro_key = str(r["_sro_key"]).strip()
        dire = r["direcao"]

        # Obter horários dos setups
        setup1 = parse_time(r.get("setup_1") or r.get("setup1"))
        setup2 = parse_time(r.get("setup_2") or r.get("setup2"))
        setup3 = parse_time(r.get("setup_3") or r.get("setup3"))
        setup4 = time(14, 0, 0)  # Fixo às 14:00

        # Verificar se setup2 e setup4 estão NULL
        setup2_is_null = pd.isna(setup2) or setup2 is None
        setup4_is_null = pd.isna(setup4) or setup4 is None

        # Definir intervalos de tempo
        if setup_number == 1:
            start_dt = datetime.combine(selected_date - timedelta(days=1), time(20, 0))
            end_dt = datetime.combine(selected_date, setup1 or time(6, 0, 0))
        elif setup_number == 2:
            start_dt = datetime.combine(selected_date, setup1 or time(6, 0, 0))
            end_dt = datetime.combine(selected_date, setup2 or time(8, 40, 0))
        elif setup_number == 3:
            start_dt = datetime.combine(selected_date, setup2 or time(8, 40, 0))
            end_dt = datetime.combine(selected_date, setup3 or time(10, 0, 0))
        else:  # setup_number == 4
            # Se setup2 e setup4 estiverem NULL, contar desde 00:00 até 14:00
            if setup2_is_null and setup4_is_null:
                start_dt = datetime.combine(selected_date, time(0, 0, 0))
            else:
                start_dt = datetime.combine(selected_date, setup3 or time(10, 0, 0))
            end_dt = datetime.combine(selected_date, setup4)

        df_sro_objs = df_obj[df_obj["_cod_sro"] == sro_key].copy()

        if df_sro_objs.empty:
            cnt = 0
            df_match = pd.DataFrame()
        else:
            if 'datetime_lanc' not in df_sro_objs.columns:
                df_sro_objs['datetime_lanc'] = pd.to_datetime(
                    df_sro_objs['data_lanc'].astype(str) + ' ' + df_sro_objs['hora_obj'].astype(str),
                    errors='coerce'
                )

            mask = (df_sro_objs['datetime_lanc'] >= start_dt) & (df_sro_objs['datetime_lanc'] <= end_dt)
            df_match = df_sro_objs[mask]
            cnt = len(df_match)

        rows.append({
            "direcao": dire,
            "sro": sro_key,
            "count": int(cnt),
            "setup_time": end_dt.time().strftime("%H:%M:%S")
        })

        if cnt > 0:
            df_match = df_match.copy()
            df_match["_direcao"] = dire
            df_match["_setup_number"] = setup_number
            df_match["_setup_time"] = end_dt.time().strftime("%H:%M:%S")
            matches.append(df_match)

    df_counts = pd.DataFrame(rows)
    df_matches = pd.concat(matches, ignore_index=True) if matches else pd.DataFrame()

    # Cálculo do percentual
    total_por_sro = df_obj.groupby("_cod_sro").size().reset_index(name="total")
    df_counts = df_counts.merge(total_por_sro, left_on="sro", right_on="_cod_sro", how="left")
    df_counts["total"] = df_counts["total"].fillna(0).astype(int)
    df_counts["percentual"] = np.where(
        df_counts["total"] > 0,
        (df_counts["count"] / df_counts["total"] * 100).round(1),
        0
    )

    return df_counts, df_matches


# ... (código anterior mantido)

def show_setup_charts(setup_number, df_counts, df_matches):
    """Exibe os gráficos para um setup específico"""
    st.markdown(f"### Setup {setup_number}")

    fig_cnt = px.bar(
        df_counts,
        x="direcao",
        y="count",
        text="count",
        title=f"Objetos até o Setup {setup_number}",
        labels={"direcao": "Direção", "count": "Qtd. Objetos"}
    )
    fig_cnt.update_traces(textposition="outside")
    st.plotly_chart(fig_cnt, use_container_width=True)

    fig_pct = px.bar(
        df_counts,
        x="direcao",
        y="percentual",
        text="percentual",
        title=f"Percentual de objetos entregues até o Setup {setup_number}",
        labels={"direcao": "Direção", "percentual": "% até o Setup"}
    )
    fig_pct.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig_pct, use_container_width=True)

    if not df_matches.empty:
        with st.expander(f"Ver objetos do Setup {setup_number}"):
            st.dataframe(df_matches)


# ... (código anterior mantido até a função load_data_for_date)

def main():
    st.title("📦 Objetos por Setup")

    selected_date = st.date_input("Selecione a data:", date.today())
    df_obj, df_mat = load_data_for_date(selected_date)

    directions_sel = st.multiselect("Filtrar direções:", sorted(df_mat["direcao"].unique()))

    setup_number = st.selectbox("Escolha o setup:", [1, 2, 3, 'resto objetos', 'todos os setups'])
    todos_setup = st.button("Mostrar Todos os setups")

    if todos_setup:
        # Monta DataFrame com todos setups
        df_list = []
        for sn in [1, 2, 3, 'resto objetos', 'todos os setups']:
            df_counts, df_matches = count_objects_until_setup(df_obj, df_mat, directions_sel, sn, selected_date)
            df_counts["setup_number"] = sn
            df_list.append(df_counts)
        df_all = pd.concat(df_list, ignore_index=True)

        st.subheader("📊 Quantidade de objetos por Setup")
        fig_cnt = px.bar(
            df_all,
            x="direcao",
            y="count",
            color="setup_number",
            barmode="stack",   # <<< agora empilhado
            text="count",
            title="Objetos por Setup",
            labels={"direcao": "Direção", "count": "Qtd. Objetos", "setup_number": "Setup"}
        )
        fig_cnt.update_traces(textposition="inside")
        st.plotly_chart(fig_cnt, use_container_width=True)

        st.subheader("📊 Percentual de objetos por Setup")
        fig_pct = px.bar(
            df_all,
            x="direcao",
            y="percentual",
            color="setup_number",
            barmode="stack",   # <<< empilhado também no percentual
            text="percentual",
            title="Percentual de objetos por Setup",
            labels={"direcao": "Direção", "percentual": "% até o Setup", "setup_number": "Setup"}
        )
        fig_pct.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
        st.plotly_chart(fig_pct, use_container_width=True)

    else:
        # Mostra apenas o setup escolhido
        df_counts, df_matches = count_objects_until_setup(df_obj, df_mat, directions_sel, setup_number, selected_date)

        st.subheader(f"📊 Quantidade de objetos até Setup {setup_number}")
        fig_cnt = px.bar(
            df_counts,
            x="direcao",
            y="count",
            text="count",
            title=f"Objetos até o Setup {setup_number}",
            labels={"direcao": "Direção", "count": "Qtd. Objetos"}
        )
        fig_cnt.update_traces(textposition="outside")
        st.plotly_chart(fig_cnt, use_container_width=True)

        st.subheader(f"📊 Percentual de objetos até Setup {setup_number}")
        fig_pct = px.bar(
            df_counts,
            x="direcao",
            y="percentual",
            text="percentual",
            title=f"Percentual de objetos entregues até o Setup {setup_number}",
            labels={"direcao": "Direção", "percentual": "% até o Setup"}
        )
        fig_pct.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(fig_pct, use_container_width=True)





# ... (restante do código mantido)

# def main():
#     st.title("📦 Objetos por Setup")
#
#     selected_date = st.date_input("Selecione a data:", date.today())
#     df_obj, df_mat = load_data_for_date(selected_date)
#
#     setup_number = st.selectbox("Escolha o setup:", [1, 2, 3, 4])
#
#     directions_sel = st.multiselect("Filtrar direções:", sorted(df_mat["direcao"].unique()))
#
#     todos_setup = st.button("Mostrar Todos os setups", )
#
#     df_counts, df_matches = count_objects_until_setup(df_obj, df_mat, directions_sel, setup_number,selected_date)
#     # Chamada corrigida
#
#
#     st.subheader(f"📊 Quantidade de objetos até Setup {setup_number}")
#     fig_cnt = px.bar(
#         df_counts,
#         x="direcao",
#         y="count",
#         text="count",
#         title=f"Objetos até o Setup {setup_number}",
#         labels={"direcao": "Direção", "count": "Qtd. Objetos"}
#     )
#     fig_cnt.update_traces(textposition="outside")
#     st.plotly_chart(fig_cnt, use_container_width=True)
#
#     st.subheader(f"📊 Percentual de objetos até Setup {setup_number}")
#     fig_pct = px.bar(
#         df_counts,
#         x="direcao",
#         y="percentual",
#         text="percentual",
#         title=f"Percentual de objetos entregues até o Setup {setup_number}",
#         labels={"direcao": "Direção", "percentual": "% até o Setup"}
#     )
#     fig_pct.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
#     st.plotly_chart(fig_pct, use_container_width=True)


if __name__ == "__main__":
    main()

# %% [markdown]
# # Registro de Operaciones Bitso - Streamlit

# %%
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# %% [markdown]
# ## Configuración inicial

# %%
ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"
NEGOCIACIONES_SHEET = "Negociaciones"
INGRESOS_SHEET = "Ingresos"

# Inicializa el archivo si no existe
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=["Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "ID"]).to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
            pd.DataFrame(columns=["Fecha", "Hora Ingreso", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)"]).to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# Carga datos

def cargar_datos():
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=NEGOCIACIONES_SHEET)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=INGRESOS_SHEET)
    return df_neg, df_ing

# Guarda datos

def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl", mode="w") as writer:
        df_neg.to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
        df_ing.to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# Valida hora

def parse_hora(texto):
    try:
        return datetime.strptime(texto.strip(), "%H:%M").time()
    except:
        return None

# Formato COP

def input_cop(label):
    raw = st.text_input(label, value="", placeholder="Ej: 5000000")
    raw = raw.replace(".", "").replace(",", "").strip()
    try:
        return float(raw)
    except:
        return 0.0

# %%
st.set_page_config(layout="centered", page_title="Registro Operaciones Bitso")
st.title("Control de Operaciones Bitso")
init_excel()
df_neg, df_ing = cargar_datos()

# === Registro de Negociación ===
st.header("1. Datos del Operador")
with st.form("form_operador"):
    fecha = st.date_input("Fecha de la operación", value=datetime.now().date())
    monto = input_cop("Monto en USDT")
    tasa = input_cop("Tasa negociada")
    hora_texto = st.text_input("Hora de negociación (HH:MM)", value="00:00")
    hora = parse_hora(hora_texto)

    submit_op = st.form_submit_button("Registrar Negociación")
    if submit_op:
        if not hora:
            st.error("Formato de hora incorrecto. Usa HH:MM")
        else:
            esperado = monto * tasa
            id_op = f"{fecha}_{hora.strftime('%H%M%S')}"
            df_neg = pd.concat([df_neg, pd.DataFrame([{
                "Fecha": fecha,
                "Hora": hora.strftime("%H:%M"),
                "Monto USDT": monto,
                "Tasa": tasa,
                "Esperado COP": esperado,
                "Estado": "Pendiente",
                "ID": id_op
            }])], ignore_index=True)
            guardar_datos(df_neg, df_ing)
            st.success(f"Operación registrada con ID: {id_op}")

# === Registro de Ingreso ===
st.markdown("---")
st.header("2. Datos de Tesorería (Ingreso COP)")
with st.form("form_ingreso"):
    fecha_ing = st.date_input("Fecha del ingreso", value=datetime.now().date(), key="fecha_tes")
    hora_text = st.text_input("Hora de ingreso del dinero (HH:MM)", value="00:00")
    hora_ing = parse_hora(hora_text)
    valor = input_cop("Valor recibido en COP")
    canal = st.selectbox("Canal de ingreso", ["Coink", "Coopcentral"])

    # Mostrar operaciones pendientes de ese día
    pendientes_dia = df_neg[(df_neg["Fecha"] == fecha_ing) & (df_neg["Estado"] == "Pendiente")]
    opciones = pendientes_dia["ID"].tolist()
    seleccionadas = st.multiselect("Selecciona las operaciones a las que se asigna este ingreso", opciones)

    submit_tes = st.form_submit_button("Registrar o actualizar operación")

    if submit_tes:
        if not hora_ing:
            st.error("Formato de hora de ingreso inválido")
        else:
            total_esperado = df_neg[df_neg["ID"].isin(seleccionadas)]["Esperado COP"].sum()
            diferencia = valor - total_esperado
            demora = None
            if seleccionadas:
                primera = df_neg[df_neg["ID"] == seleccionadas[0]].iloc[0]
                dt1 = datetime.strptime(f"{primera['Fecha']} {primera['Hora']}", "%Y-%m-%d %H:%M")
                dt2 = datetime.combine(fecha_ing, hora_ing)
                demora = round((dt2 - dt1).total_seconds() / 60, 2)

                for sid in seleccionadas:
                    df_neg.loc[df_neg["ID"] == sid, "Estado"] = "Pagado"

            df_ing = pd.concat([df_ing, pd.DataFrame([{
                "Fecha": fecha_ing,
                "Hora Ingreso": hora_ing.strftime("%H:%M"),
                "Valor Recibido": valor,
                "Canal": canal,
                "Asignado a": ", ".join(seleccionadas),
                "Diferencia": diferencia,
                "Demora (min)": demora
            }])], ignore_index=True)

            guardar_datos(df_neg, df_ing)
            st.success(f"Ingreso registrado y asignado a: {', '.join(seleccionadas)}")

# === Historial ===
st.markdown("---")
st.subheader("Historial de Operaciones")
tabs = st.tabs(["Negociaciones", "Ingresos"])

with tabs[0]:
    st.dataframe(df_neg.sort_values("Fecha", ascending=False), use_container_width=True)

with tabs[1]:
    st.dataframe(df_ing.sort_values("Fecha", ascending=False), use_container_width=True)

# === Descargar ===
st.download_button(
    "Descargar Historial Completo",
    data=open(ARCHIVO_EXCEL, "rb"),
    file_name=ARCHIVO_EXCEL,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)






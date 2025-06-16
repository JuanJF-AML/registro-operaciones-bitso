import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"
SHEET_NEGOCIACIONES = "Negociaciones"
SHEET_INGRESOS = "Ingresos"

# Inicializa el archivo Excel si no existe
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=["ID", "Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "Observación"]).to_excel(writer, sheet_name=SHEET_NEGOCIACIONES, index=False)
            pd.DataFrame(columns=["Fecha", "Hora", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)", "Observación"]).to_excel(writer, sheet_name=SHEET_INGRESOS, index=False)

def cargar_datos():
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=SHEET_NEGOCIACIONES)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=SHEET_INGRESOS)
    return df_neg, df_ing

def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl", mode="w") as writer:
        df_neg.to_excel(writer, sheet_name=SHEET_NEGOCIACIONES, index=False)
        df_ing.to_excel(writer, sheet_name=SHEET_INGRESOS, index=False)

def formatear_estado(estado):
    if estado == "Pagado":
        return "✅ Pagado"
    elif estado == "Parcial":
        return "🔄 Parcial"
    return "❌ Pendiente"

# ===================== UI STREAMLIT =====================
st.set_page_config(page_title="Bitso - Registro de Operaciones", layout="centered")
st.title("📋 Registro de Operaciones Bitso")
init_excel()
df_neg, df_ing = cargar_datos()

# === REGISTRO DE NEGOCIACIÓN ===
st.header("🧾 Registrar Negociación")
with st.form("form_negociacion"):
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", value=datetime.now().date())
        monto_usdt = st.number_input("Monto USDT", format="%.2f", min_value=0.0, step=0.01)
        tasa = st.number_input("Tasa negociada", format="%.2f", min_value=0.0)
    with col2:
        hora = st.text_input("Hora negociación (HH:MM)", value=datetime.now().strftime("%H:%M"))
        obs = st.text_area("Observación (opcional)", height=100)

    enviar = st.form_submit_button("Registrar Negociación")
    if enviar:
        esperado = monto_usdt * tasa
        id_op = f"{fecha}_{hora.replace(':','')}"
        df_neg = pd.concat([df_neg, pd.DataFrame([{
            "ID": id_op,
            "Fecha": fecha,
            "Hora": hora,
            "Monto USDT": monto_usdt,
            "Tasa": tasa,
            "Esperado COP": esperado,
            "Estado": "Pendiente",
            "Observación": obs
        }])], ignore_index=True)
        guardar_datos(df_neg, df_ing)
        st.success(f"Negociación registrada con ID: `{id_op}`")

# === REGISTRO DE INGRESO ===
st.header("🏦 Registrar Ingreso")
with st.form("form_ingreso"):
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha ingreso", value=datetime.now().date(), key="fecha_ing")
        valor = st.number_input("Valor recibido (COP)", format="%.2f", min_value=0.0, step=100.0)
    with col2:
        hora = st.text_input("Hora ingreso (HH:MM)", value=datetime.now().strftime("%H:%M"), key="hora_ing")
        canal = st.selectbox("Canal", ["Coink", "Coopcentral"])
    obs_ing = st.text_area("Observación ingreso", height=100)

    # Selección manual
    pendientes = df_neg[df_neg["Estado"].isin(["Pendiente", "Parcial"])]
    pendientes = pendientes.sort_values(["Fecha", "Hora"])
    seleccionables = pendientes["ID"] + " | " + pendientes["Esperado COP"].map("{:,.0f}".format)
    seleccionadas = st.multiselect("Asignar ingreso a operaciones:", seleccionables)

    confirmar = st.form_submit_button("Registrar Ingreso")
    if confirmar:
        asignaciones = []
        total_asignado = 0.0

        for sel in seleccionadas:
            id_sel = sel.split(" | ")[0]
            idx = df_neg[df_neg["ID"] == id_sel].index[0]
            esperado = df_neg.at[idx, "Esperado COP"]

            if total_asignado + esperado <= valor:
                df_neg.at[idx, "Estado"] = "Pagado"
                asignaciones.append(id_sel)
                total_asignado += esperado
            elif valor > total_asignado:
                df_neg.at[idx, "Esperado COP"] = esperado - (valor - total_asignado)
                df_neg.at[idx, "Estado"] = "Parcial"
                asignaciones.append(id_sel + " (Parcial)")
                total_asignado = valor
                break

        diferencia = round(valor - total_asignado, 2)
        demora = None
        if asignaciones:
            id_ref = asignaciones[0].replace(" (Parcial)", "")
            fila = df_neg[df_neg["ID"] == id_ref].iloc[0]
            dt_op = datetime.strptime(f"{fila['Fecha']} {fila['Hora']}", "%Y-%m-%d %H:%M")
            dt_ing = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
            demora = round((dt_ing - dt_op).total_seconds() / 60, 2)

        df_ing = pd.concat([df_ing, pd.DataFrame([{
            "Fecha": fecha,
            "Hora": hora,
            "Valor Recibido": valor,
            "Canal": canal,
            "Asignado a": ", ".join(asignaciones),
            "Diferencia": diferencia,
            "Demora (min)": demora,
            "Observación": obs_ing
        }])], ignore_index=True)

        guardar_datos(df_neg, df_ing)
        st.success("Ingreso registrado exitosamente.")

# === RESUMEN DEL DÍA ===
st.markdown("---")
st.header("📊 Resumen Diario")
hoy = datetime.now().date()
neg_hoy = df_neg[df_neg["Fecha"] == hoy]
ing_hoy = df_ing[df_ing["Fecha"] == hoy]

total_esperado = neg_hoy["Monto USDT"].sum() * neg_hoy["Tasa"].mean() if not neg_hoy.empty else 0
total_ingresado = ing_hoy["Valor Recibido"].sum()
porcentaje = (total_ingresado / total_esperado) * 100 if total_esperado else 0

col1, col2, col3 = st.columns(3)
col1.metric("💵 Negociado Hoy (COP)", f"${total_esperado:,.0f}")
col2.metric("🏦 Ingresado Hoy", f"${total_ingresado:,.0f}")
col3.metric("📈 % Cumplimiento", f"{porcentaje:.1f}%")

# === HISTORIAL COMPLETO ===
st.markdown("---")
st.header("📁 Historial Completo")
tab1, tab2 = st.tabs(["Negociaciones", "Ingresos"])

with tab1:
    df_tmp = df_neg.copy()
    df_tmp["Estado"] = df_tmp["Estado"].apply(formatear_estado)
    df_tmp["Esperado COP"] = df_tmp["Esperado COP"].map("{:,.0f}".format)
    st.dataframe(df_tmp.sort_values("Fecha", ascending=False), use_container_width=True)

with tab2:
    df_tmp = df_ing.copy()
    df_tmp["Valor Recibido"] = df_tmp["Valor Recibido"].map("{:,.0f}".format)
    st.dataframe(df_tmp.sort_values("Fecha", ascending=False), use_container_width=True)

# === DESCARGA EXCEL ===
st.download_button(
    label="⬇️ Descargar Excel Completo",
    data=open(ARCHIVO_EXCEL, "rb"),
    file_name=ARCHIVO_EXCEL,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)





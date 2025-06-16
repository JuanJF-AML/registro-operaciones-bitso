# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# === CONFIGURACIÓN ===
ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"
NEGOCIACIONES_SHEET = "Negociaciones"
INGRESOS_SHEET = "Ingresos"

# === INICIALIZAR EXCEL SI NO EXISTE ===
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=[
                "Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "Observación", "ID"
            ]).to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
            pd.DataFrame(columns=[
                "Fecha", "Hora Ingreso", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)", "Observación"
            ]).to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# === CARGAR DATOS ===
def cargar_datos():
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=NEGOCIACIONES_SHEET)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=INGRESOS_SHEET)
    return df_neg, df_ing

# === GUARDAR DATOS ===
def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl", mode="w") as writer:
        df_neg.to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
        df_ing.to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# === APLICACIÓN PRINCIPAL ===
st.set_page_config(layout="wide", page_title="Operaciones Bitso")
st.title("📋 Control Diario de Operaciones Bitso")

init_excel()
df_neg, df_ing = cargar_datos()

# === SECCIÓN OPERADOR ===
with st.expander("🧾 Registro de Negociación (Operador)", expanded=True):
    with st.form("form_operador"):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha de negociación", value=datetime.now().date())
            monto = st.number_input("Monto USDT", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            hora = st.text_input("Hora (formato HH:MM)", value=datetime.now().strftime("%H:%M"))
            tasa = st.number_input("Tasa negociada", min_value=0.0, step=1.0)

        observacion = st.text_input("Observación (opcional)")
        submit_op = st.form_submit_button("Registrar Negociación")

        if submit_op:
            esperado = monto * tasa
            id_op = f"{fecha}_{hora.replace(':', '')}"
            df_neg = pd.concat([df_neg, pd.DataFrame([{
                "Fecha": fecha,
                "Hora": hora,
                "Monto USDT": monto,
                "Tasa": tasa,
                "Esperado COP": esperado,
                "Estado": "Pendiente",
                "Observación": observacion,
                "ID": id_op
            }])], ignore_index=True)
            guardar_datos(df_neg, df_ing)
            st.success(f"Negociación registrada con ID: {id_op}")

# === SECCIÓN TESORERÍA ===
with st.expander("🏦 Registro de Ingreso (Tesorería)", expanded=True):
    with st.form("form_tesoreria"):
        fecha_ing = st.date_input("Fecha del ingreso", value=datetime.now().date(), key="fecha_tes")
        hora_ing = st.text_input("Hora del ingreso (HH:MM)", value=datetime.now().strftime("%H:%M"))
        valor = st.number_input("Valor recibido en COP", min_value=0.0, step=100.0, format="%.0f")
        canal = st.selectbox("Canal de ingreso", ["Coink", "Coopcentral"])
        obs_ing = st.text_input("Observación ingreso (opcional)")

        # Selección de operaciones pendientes por día
        operaciones_dia = df_neg[(df_neg["Fecha"] == fecha_ing) & (df_neg["Estado"] != "Pagado")]
        seleccionadas = st.multiselect("Selecciona operaciones a asociar", operaciones_dia["ID"].tolist())

        submit_tes = st.form_submit_button("Registrar Ingreso")
        if submit_tes:
            suma_esperado = df_neg[df_neg["ID"].isin(seleccionadas)]["Esperado COP"].sum()
            diferencia = valor - suma_esperado
            demora = None
            if seleccionadas:
                primera_op = df_neg[df_neg["ID"] == seleccionadas[0]].iloc[0]
                dt_neg = datetime.combine(primera_op["Fecha"], datetime.strptime(primera_op["Hora"], "%H:%M").time())
                dt_ing = datetime.combine(fecha_ing, datetime.strptime(hora_ing, "%H:%M").time())
                demora = round((dt_ing - dt_neg).total_seconds() / 60, 2)

                for idx, op in df_neg[df_neg["ID"].isin(seleccionadas)].iterrows():
                    esperado = op["Esperado COP"]
                    if valor >= esperado:
                        df_neg.loc[df_neg["ID"] == op["ID"], "Estado"] = "Pagado"
                        valor -= esperado
                    elif valor > 0:
                        df_neg.loc[df_neg["ID"] == op["ID"], "Esperado COP"] -= valor
                        df_neg.loc[df_neg["ID"] == op["ID"], "Estado"] = "Parcial"
                        valor = 0

            df_ing = pd.concat([df_ing, pd.DataFrame([{
                "Fecha": fecha_ing,
                "Hora Ingreso": hora_ing,
                "Valor Recibido": valor + suma_esperado,
                "Canal": canal,
                "Asignado a": ", ".join(seleccionadas),
                "Diferencia": diferencia,
                "Demora (min)": demora,
                "Observación": obs_ing
            }])], ignore_index=True)

            guardar_datos(df_neg, df_ing)
            st.success("Ingreso registrado correctamente")

# === RESUMEN Y ESTADO ===
st.markdown("---")
st.subheader("📈 Resumen Diario")
hoy = datetime.now().date()
op_hoy = df_neg[df_neg["Fecha"] == hoy]
ing_hoy = df_ing[df_ing["Fecha"] == hoy]

col1, col2, col3 = st.columns(3)
col1.metric("Total Operado (USDT)", f"{op_hoy['Monto USDT'].sum():,.2f}")
col2.metric("Ingresado a Bancos (COP)", f"{ing_hoy['Valor Recibido'].sum():,.0f}")
total_esperado = op_hoy["Tasa"].multiply(op_hoy["Monto USDT"]).sum()
porcentaje = (ing_hoy["Valor Recibido"].sum() / total_esperado * 100) if total_esperado else 0
col3.metric("Cumplimiento (%)", f"{porcentaje:.2f}%")

# === HISTORIAL COMPLETO ===
st.markdown("---")
tabs = st.tabs(["📋 Negociaciones", "🏦 Ingresos", "⬇️ Exportar"])

with tabs[0]:
    df_show = df_neg.copy()
    df_show["Estado"] = df_show["Estado"].map({
        "Pagado": "✅ Pagado",
        "Pendiente": "❌ Pendiente",
        "Parcial": "🔄 Parcial"
    }).fillna("❓")
    st.dataframe(df_show.sort_values("Fecha", ascending=False), use_container_width=True)

with tabs[1]:
    st.dataframe(df_ing.sort_values("Fecha", ascending=False), use_container_width=True)

with tabs[2]:
    st.download_button(
        label="📥 Descargar Excel Completo",
        data=open(ARCHIVO_EXCEL, "rb"),
        file_name=ARCHIVO_EXCEL,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )





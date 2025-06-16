import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# === CONFIGURACIÓN INICIAL ===
ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"

# Inicializa el archivo Excel si no existe
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        df = pd.DataFrame(columns=[
            "Fecha Operación", "Monto USDT", "Tasa Negociada", "Valor esperado COP",
            "Hora Negociación", "Valor Recibido COP", "Hora Ingreso",
            "Canal", "Diferencia", "Demora(min)"
        ])
        df.to_excel(ARCHIVO_EXCEL, index=False)

# Registrar o actualizar operación
def registrar_operacion(data):
    df = pd.read_excel(ARCHIVO_EXCEL)
    clave = (data["Fecha Operación"], data.get("Monto USDT"), data.get("Tasa Negociada"))

    match = df[(df["Fecha Operación"] == clave[0]) &
               (df["Monto USDT"] == clave[1]) &
               (df["Tasa Negociada"] == clave[2])]

    if not match.empty:
        idx = match.index[0]
        for col, val in data.items():
            if val is not None:
                df.at[idx, col] = val
    else:
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)

    df.to_excel(ARCHIVO_EXCEL, index=False)

# === STREAMLIT ===
st.set_page_config(layout="centered", page_title="Registro de Operaciones Bitso")
st.title("Control de Operaciones Bitso")
init_excel()

# === ROL ===
rol = st.radio("¿Qué rol estás registrando?", ["Operador", "Tesorería"])
deshabilitado_op = rol == "Tesorería"
deshabilitado_teso = rol == "Operador"

with st.form("form_operacion"):
    st.subheader("1. Datos del Operador")

    fecha = st.date_input("Fecha de la operación", value=datetime.now().date(), disabled=False)
    monto_usdt = st.number_input("Monto en USDT", min_value=0.0, step=0.01, disabled=deshabilitado_op)
    tasa = st.number_input("Tasa negociada", min_value=0.0, step=1.0, disabled=deshabilitado_op)
    hora_neg = st.time_input("Hora de negociación", disabled=deshabilitado_op)

    st.markdown("---")
    st.subheader("2. Datos de Tesorería (Ingreso COP)")

    valor_recibido = st.number_input("Valor recibido en COP", min_value=0.0, step=100.0, disabled=deshabilitado_teso)
    hora_ingreso = st.time_input("Hora de ingreso del dinero", disabled=deshabilitado_teso)
    canal = st.selectbox("Canal de ingreso", ["", "Coink", "Coopcentral"], disabled=deshabilitado_teso)

    submitted = st.form_submit_button("Registrar o actualizar operación")

    if submitted:
        esperado = monto_usdt * tasa if monto_usdt and tasa else None
        diferencia = abs(valor_recibido - esperado) if esperado and valor_recibido else None
        demora = (
            (datetime.combine(fecha, hora_ingreso) - datetime.combine(fecha, hora_neg)).total_seconds() / 60
            if hora_ingreso and hora_neg else None
        )

        datos = {
            "Fecha Operación": fecha,
            "Monto USDT": monto_usdt if not deshabilitado_op else None,
            "Tasa Negociada": tasa if not deshabilitado_op else None,
            "Valor esperado COP": esperado if not deshabilitado_op else None,
            "Hora Negociación": hora_neg.strftime("%H:%M") if not deshabilitado_op else None,
            "Valor Recibido COP": valor_recibido if not deshabilitado_teso else None,
            "Hora Ingreso": hora_ingreso.strftime("%H:%M") if not deshabilitado_teso else None,
            "Canal": canal if not deshabilitado_teso else None,
            "Diferencia": diferencia if diferencia else None,
            "Demora(min)": round(demora, 2) if demora is not None else None
        }

        registrar_operacion(datos)

        if diferencia and diferencia >= 1000:
            st.warning(f"Diferencia entre esperado y recibido: {diferencia:,.0f} COP.")
        elif diferencia:
            st.success(f"Diferencia aceptable: {diferencia:,.0f} COP.")

        if demora is not None:
            st.info(f"Tiempo entre negociación e ingreso: {round(demora)} minutos.")

        st.success("Registro actualizado correctamente.")

# === HISTORIAL ===
st.markdown("---")
st.subheader("Historial de Operaciones")

try:
    df_historial = pd.read_excel(ARCHIVO_EXCEL)
    st.dataframe(df_historial.sort_values("Fecha Operación", ascending=False), use_container_width=True)

    resumen = df_historial.groupby(["Fecha Operación", "Canal"]).agg({
        "Valor esperado COP": "sum",
        "Valor Recibido COP": "sum",
        "Diferencia": "sum",
        "Demora(min)": "mean"
    }).round(2).reset_index()

    st.subheader("Resumen Diario por Canal")
    st.dataframe(resumen, use_container_width=True)

    st.download_button(
        label="Descargar Historial de Operaciones",
        data=open(ARCHIVO_EXCEL, "rb"),
        file_name=ARCHIVO_EXCEL,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
except Exception as e:
    st.warning(f"No se pudo cargar el historial: {e}")





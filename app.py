# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"
HOJA_NEG = "Negociaciones"
HOJA_ING = "Ingresos"

# Inicializa el archivo si no existe
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=["Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "ID", "Observacion"]).to_excel(writer, sheet_name=HOJA_NEG, index=False)
            pd.DataFrame(columns=["Fecha", "Hora Ingreso", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)", "Observacion"]).to_excel(writer, sheet_name=HOJA_ING, index=False)

# Carga ambos dataframes
def cargar_datos():
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=HOJA_NEG)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=HOJA_ING)
    df_neg["Fecha"] = pd.to_datetime(df_neg["Fecha"]).dt.date
    df_ing["Fecha"] = pd.to_datetime(df_ing["Fecha"]).dt.date
    return df_neg, df_ing

# Guarda ambos dataframes
def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
        df_neg.to_excel(writer, sheet_name=HOJA_NEG, index=False)
        df_ing.to_excel(writer, sheet_name=HOJA_ING, index=False)

# === INICIO STREAMLIT ===
st.set_page_config(layout="wide", page_title="Registro Bitso")
st.sidebar.title("📋 Registro de Operaciones Bitso")
opcion = st.sidebar.radio("Ir a:", ["📑 Registro de Operaciones", "📂 Historial y Reportes"])

init_excel()
df_neg, df_ing = cargar_datos()

if opcion == "📑 Registro de Operaciones":
    rol = st.radio("¿Qué rol estás registrando?", ["🧾 Operador", "💳 Tesorería"], horizontal=True)

    if rol == "🧾 Operador":
        st.header("🧾 Registro de Negociación (Operador)")
        with st.form("form_op"):
            fecha = st.date_input("Fecha")
            hora = st.text_input("Hora de negociación (HH:MM)")
            monto = st.number_input("Monto USDT", min_value=0.0, step=1.0, format="%.2f")
            tasa = st.number_input("Tasa negociada", min_value=0.0, step=1.0)
            obs = st.text_area("Observación (opcional)")
            boton = st.form_submit_button("Registrar Negociación")
            if boton:
                esperado = monto * tasa
                id_op = f"{fecha}_{hora.replace(':','')}"
                df_neg = pd.concat([df_neg, pd.DataFrame([{
                    "Fecha": fecha,
                    "Hora": hora,
                    "Monto USDT": monto,
                    "Tasa": tasa,
                    "Esperado COP": esperado,
                    "Estado": "Pendiente",
                    "ID": id_op,
                    "Observacion": obs
                }])], ignore_index=True)
                guardar_datos(df_neg, df_ing)
                st.success(f"Negociación registrada con ID: {id_op}")

    elif rol == "💳 Tesorería":
        st.header("💳 Registro de Ingreso (Tesorería)")
        with st.form("form_teso"):
            fecha_ing = st.date_input("Fecha del ingreso")
            hora_ing = st.text_input("Hora del ingreso (HH:MM)")
            valor = st.number_input("Valor recibido en COP", min_value=0.0, step=100.0, format="%.0f")
            canal = st.selectbox("Canal", ["Coink", "Coopcentral"])
            obs_teso = st.text_area("Observación (opcional)")

            ops_pendientes = df_neg[(df_neg["Estado"] != "Pagado") & (df_neg["Fecha"] == fecha_ing)]
            opciones = ops_pendientes["ID"].tolist()
            seleccionadas = st.multiselect("Selecciona operaciones a asignar", opciones)

            boton_tes = st.form_submit_button("Registrar Ingreso")
            if boton_tes:
                if not seleccionadas:
                    st.warning("⚠️ Debes seleccionar al menos una operación para asignar.")
                else:
                    total_esperado = df_neg[df_neg["ID"].isin(seleccionadas)]["Esperado COP"].sum()
                    diferencia = valor - total_esperado

                    for op_id in seleccionadas:
                        idx = df_neg[df_neg["ID"] == op_id].index[0]
                        if valor >= df_neg.at[idx, "Esperado COP"]:
                            df_neg.at[idx, "Estado"] = "Pagado"
                        else:
                            df_neg.at[idx, "Estado"] = "Parcial"

                    # demora calculada con la primera op
                    primera = df_neg[df_neg["ID"] == seleccionadas[0]]
                    dt_op = datetime.strptime(f"{primera['Fecha'].values[0]} {primera['Hora'].values[0]}", "%Y-%m-%d %H:%M")
                    dt_ing = datetime.strptime(f"{fecha_ing} {hora_ing}", "%Y-%m-%d %H:%M")
                    demora = round((dt_ing - dt_op).total_seconds() / 60, 2)

                    df_ing = pd.concat([df_ing, pd.DataFrame([{
                        "Fecha": fecha_ing,
                        "Hora Ingreso": hora_ing,
                        "Valor Recibido": valor,
                        "Canal": canal,
                        "Asignado a": ", ".join(seleccionadas),
                        "Diferencia": diferencia,
                        "Demora (min)": demora,
                        "Observacion": obs_teso
                    }])], ignore_index=True)
                    guardar_datos(df_neg, df_ing)
                    st.success(f"Ingreso registrado por {valor:,.0f} y asignado a: {', '.join(seleccionadas)}")

elif opcion == "📂 Historial y Reportes":
    st.title("📂 Historial y Reportes")
    col1, col2, col3 = st.columns(3)
    hoy = datetime.now().date()
    total_hoy = df_neg[df_neg["Fecha"] == hoy]["Esperado COP"].sum()
    ingresado_hoy = df_ing[df_ing["Fecha"] == hoy]["Valor Recibido"].sum()
    cumplimiento = (ingresado_hoy / total_hoy * 100) if total_hoy > 0 else 0

    col1.metric("💵 Negociado Hoy (COP)", f"${total_hoy:,.0f}")
    col2.metric("🏦 Ingresado Hoy", f"${ingresado_hoy:,.0f}")
    col3.metric("📈 % Cumplimiento", f"{cumplimiento:.1f}%")

    st.subheader("📁 Historial Completo")
    tab1, tab2 = st.tabs(["Negociaciones", "Ingresos"])

    with tab1:
        colores = {
            "Pagado": "✅",
            "Parcial": "🔄",
            "Pendiente": "❌"
        }
        df_mostrar = df_neg.copy()
        df_mostrar["Estado"] = df_mostrar["Estado"].map(colores)
        st.dataframe(df_mostrar.sort_values("Fecha", ascending=False), use_container_width=True)

    with tab2:
        st.dataframe(df_ing.sort_values("Fecha", ascending=False), use_container_width=True)

    st.download_button("📥 Descargar Excel Completo", data=open(ARCHIVO_EXCEL, "rb"), file_name=ARCHIVO_EXCEL)

    st.subheader("🗑️ Eliminar Registro")
    id_a_borrar = st.text_input("ID de la operación a eliminar")
    if st.button("Eliminar operación"):
        if id_a_borrar in df_neg["ID"].values:
            df_neg = df_neg[df_neg["ID"] != id_a_borrar]
            guardar_datos(df_neg, df_ing)
            st.success("Registro eliminado correctamente.")
        else:
            st.warning("⚠️ ID no encontrado en las negociaciones.")



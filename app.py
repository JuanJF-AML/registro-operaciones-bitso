# %% [markdown]
# ## LIBRERÍAS

# %%
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# %% [markdown]
# ## CONFIGURACIÓN INICIAL

# %%
ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"
NEGOCIACIONES_SHEET = "Negociaciones"
INGRESOS_SHEET = "Ingresos"

# Inicializa el archivo Excel si no existe
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=[
                "Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "ID", "Observación"
            ]).to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)

            pd.DataFrame(columns=[
                "Fecha", "Hora Ingreso", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)", "Observación"
            ]).to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# Carga los datos desde el archivo Excel
def cargar_datos():
    with pd.ExcelWriter(ARCHIVO_EXCEL, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
        pass
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=NEGOCIACIONES_SHEET)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=INGRESOS_SHEET)
    return df_neg, df_ing

# Guarda los datos en el archivo Excel
def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl", mode="w") as writer:
        df_neg.to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
        df_ing.to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# %% [markdown]
# ## INTERFAZ

# %%
st.set_page_config(layout="centered", page_title="Registro Operaciones Bitso")
st.title("📋 Registro de Operaciones Bitso")

init_excel()
df_neg, df_ing = cargar_datos()

menu = st.sidebar.radio("Navegación", ["Formulario", "Historial y Reportes", "Eliminar Registros"])

if menu == "Formulario":
    # === SECCIÓN OPERADOR ===
    st.subheader("🧾 Registro de Negociación (Operador)")
    with st.form("form_operador"):
        fecha = st.date_input("Fecha", value=datetime.now().date())
        hora = st.text_input("Hora Negociación (HH:MM)", value="00:00")
        monto = st.number_input("Monto USDT", min_value=0.0, step=0.01, format="%0.2f")
        tasa = st.number_input("Tasa negociada", min_value=0.0, step=1.0, format="%0.2f")
        obs = st.text_area("Observación (opcional)")

        submit_op = st.form_submit_button("Guardar Negociación")
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
                "ID": id_op,
                "Observación": obs
            }])], ignore_index=True)
            guardar_datos(df_neg, df_ing)
            st.success(f"✅ Negociación registrada con ID: {id_op}")

    # === SECCIÓN TESORERÍA ===
    st.subheader("💵 Registro de Ingreso (Tesorería)")
    with st.form("form_tesoreria"):
        fecha_ing = st.date_input("Fecha del ingreso", value=datetime.now().date(), key="fecha_tes")
        hora_ing = st.text_input("Hora del ingreso (HH:MM)", key="hora_tes")
        valor = st.number_input("Valor recibido en COP", min_value=0.0, step=100.0, format="%0.2f")
        canal = st.selectbox("Canal", ["Coink", "Coopcentral"])
        obs_tes = st.text_area("Observación (opcional)", key="obs_tes")

        df_neg["Fecha"] = pd.to_datetime(df_neg["Fecha"]).dt.date
        pendientes_dia = df_neg[(df_neg["Estado"] == "Pendiente") & (df_neg["Fecha"] == fecha_ing)]
        opciones = pendientes_dia["ID"].tolist()
        seleccionadas = st.multiselect("Selecciona operaciones a asignar", opciones)

        submit_tes = st.form_submit_button("Registrar Ingreso")
        if submit_tes:
            total_asignado = df_neg[df_neg["ID"].isin(seleccionadas)]["Esperado COP"].sum()
            diferencia = valor - total_asignado

            try:
                hora_str = hora_ing.strip()
                hora_dt = datetime.strptime(hora_str, "%H:%M").time()
                fecha_primera = df_neg[df_neg["ID"] == seleccionadas[0]]["Fecha"].values[0]
                hora_primera = df_neg[df_neg["ID"] == seleccionadas[0]]["Hora"].values[0]
                dt_neg = datetime.strptime(f"{fecha_primera} {hora_primera}", "%Y-%m-%d %H:%M")
                dt_ing = datetime.combine(fecha_ing, hora_dt)
                demora = round((dt_ing - dt_neg).total_seconds() / 60, 2)
            except:
                demora = None

            for op_id in seleccionadas:
                idx = df_neg[df_neg["ID"] == op_id].index[0]
                df_neg.at[idx, "Estado"] = "Pagado"

            df_ing = pd.concat([df_ing, pd.DataFrame([{
                "Fecha": fecha_ing,
                "Hora Ingreso": hora_ing,
                "Valor Recibido": valor,
                "Canal": canal,
                "Asignado a": ", ".join(seleccionadas),
                "Diferencia": diferencia,
                "Demora (min)": demora,
                "Observación": obs_tes
            }])], ignore_index=True)

            guardar_datos(df_neg, df_ing)
            st.success("✅ Ingreso registrado exitosamente.")

elif menu == "Historial y Reportes":
    st.subheader("📜 Historial de Operaciones")
    try:
        df_neg, df_ing = cargar_datos()
        tab1, tab2 = st.tabs(["Negociaciones", "Ingresos"])
        with tab1:
            st.dataframe(df_neg.sort_values("Fecha", ascending=False), use_container_width=True)
        with tab2:
            st.dataframe(df_ing.sort_values("Fecha", ascending=False), use_container_width=True)

        st.download_button(
            label="⬇️ Descargar Historial Completo",
            data=open(ARCHIVO_EXCEL, "rb"),
            file_name=ARCHIVO_EXCEL,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        resumen = df_ing.groupby(["Fecha", "Canal"]).agg({
            "Valor Recibido": "sum",
            "Diferencia": "sum",
            "Demora (min)": "mean"
        }).round(2).reset_index()

        st.subheader("📊 Resumen Diario por Canal")
        st.dataframe(resumen, use_container_width=True)

    except Exception as e:
        st.warning(f"No se pudo mostrar el historial: {e}")

elif menu == "Eliminar Registros":
    st.subheader("🗑️ Eliminar registros manuales")
    df_neg, df_ing = cargar_datos()
    tab1, tab2 = st.tabs(["Negociaciones", "Ingresos"])

    with tab1:
        id_borrar = st.selectbox("Selecciona negociación a eliminar", df_neg["ID"].tolist())
        if st.button("Eliminar negociación"):
            df_neg = df_neg[df_neg["ID"] != id_borrar]
            guardar_datos(df_neg, df_ing)
            st.success("Negociación eliminada.")

    with tab2:
        idxs = df_ing.index.tolist()
        idx_sel = st.selectbox("Selecciona ingreso a eliminar", idxs)
        if st.button("Eliminar ingreso"):
            df_ing = df_ing.drop(index=idx_sel).reset_index(drop=True)
            guardar_datos(df_neg, df_ing)
            st.success("Ingreso eliminado.")





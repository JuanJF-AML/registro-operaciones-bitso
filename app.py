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

def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=[
                "Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "ID"
            ]).to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)

            pd.DataFrame(columns=[
                "Fecha", "Hora Ingreso", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)"
            ]).to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

def cargar_datos():
    with pd.ExcelWriter(ARCHIVO_EXCEL, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
        pass  # solo asegura que existe
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=NEGOCIACIONES_SHEET)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=INGRESOS_SHEET)
    return df_neg, df_ing

def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl", mode="w") as writer:
        df_neg.to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
        df_ing.to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# %% [markdown]
# ## INTERFAZ

# %%
st.set_page_config(layout="centered", page_title="Registro Operaciones Bitso")
st.title("Registro de Operaciones Bitso")

init_excel()
df_neg, df_ing = cargar_datos()

# === SECCIÓN OPERADOR ===
st.subheader("🧾 Registro de Negociación (Operador)")
with st.form("form_operador"):
    fecha = st.date_input("Fecha", value=datetime.now().date())
    hora = st.time_input("Hora Negociación")
    monto = st.number_input("Monto USDT", min_value=0.0, step=0.01)
    tasa = st.number_input("Tasa negociada", min_value=0.0, step=1.0)

    submit_op = st.form_submit_button("Guardar Negociación")
    if submit_op:
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
        st.success(f"Negociación registrada con ID: {id_op}")

# === SECCIÓN TESORERÍA ===
st.subheader("Registro de Ingreso (Tesorería)")
with st.form("form_tesoreria"):
    fecha_ing = st.date_input("Fecha del ingreso", value=datetime.now().date(), key="fecha_tes")
    hora_ing = st.time_input("Hora del ingreso", key="hora_tes")
    valor = st.number_input("Valor recibido en COP", min_value=0.0, step=100.0)
    canal = st.selectbox("Canal", ["Coink", "Coopcentral"])

    submit_tes = st.form_submit_button("Registrar Ingreso")
    if submit_tes:
        pendientes = df_neg[df_neg["Estado"] == "Pendiente"].sort_values(["Fecha", "Hora"])
        valor_restante = valor
        asignaciones = []

        for idx, row in pendientes.iterrows():
            esperado = row["Esperado COP"]
            if valor_restante >= esperado:
                df_neg.at[idx, "Estado"] = "Pagado"
                asignaciones.append(row["ID"])
                valor_restante -= esperado
            elif valor_restante > 0:
                df_neg.at[idx, "Esperado COP"] -= valor_restante
                asignaciones.append(row["ID"] + " (parcial)")
                valor_restante = 0
                break
            else:
                break

        diferencia = valor - sum(df_neg[df_neg["ID"].isin(asignaciones)]["Esperado COP"])
        demora = None
        if asignaciones:
            fecha_primera = df_neg[df_neg["ID"] == asignaciones[0].replace(" (parcial)", "")]["Fecha"].values[0]
            hora_primera = df_neg[df_neg["ID"] == asignaciones[0].replace(" (parcial)", "")]["Hora"].values[0]
            dt_neg = datetime.strptime(f"{fecha_primera} {hora_primera}", "%Y-%m-%d %H:%M")
            dt_ing = datetime.combine(fecha_ing, hora_ing)
            demora = round((dt_ing - dt_neg).total_seconds() / 60, 2)

        df_ing = pd.concat([df_ing, pd.DataFrame([{
            "Fecha": fecha_ing,
            "Hora Ingreso": hora_ing.strftime("%H:%M"),
            "Valor Recibido": valor,
            "Canal": canal,
            "Asignado a": ", ".join(asignaciones) if asignaciones else "Sin asignar",
            "Diferencia": diferencia,
            "Demora (min)": demora
        }])], ignore_index=True)

        guardar_datos(df_neg, df_ing)
        st.success(f"Ingreso registrado y asignado a: {', '.join(asignaciones)}")

# === HISTORIAL ===
st.markdown("---")
st.subheader("Historial de Negociaciones e Ingresos")

tab1, tab2 = st.tabs(["Negociaciones", "Ingresos"])

with tab1:
    st.dataframe(df_neg.sort_values("Fecha", ascending=False), use_container_width=True)

with tab2:
    st.dataframe(df_ing.sort_values("Fecha", ascending=False), use_container_width=True)

# === DESCARGA EXCEL ===
st.markdown("---")
st.download_button(
    label="Descargar Excel Completo",
    data=open(ARCHIVO_EXCEL, "rb"),
    file_name="registro_operaciones_bitso.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
st.markdown("---")
st.subheader("📊 Historial y Resumen Diario")

try:
    df_ingresos = pd.read_excel(ARCHIVO_EXCEL, sheet_name="Ingresos")
    df_ingresos["Fecha"] = pd.to_datetime(df_ingresos["Fecha"]).dt.date

    st.dataframe(df_ingresos.sort_values("Fecha", ascending=False), use_container_width=True)

    resumen = df_ingresos.groupby(["Fecha", "Canal"]).agg({
        "Valor Recibido": "sum",
        "Diferencia": "sum",
        "Demora (min)": "mean"
    }).round(2).reset_index()

    st.subheader("Resumen Diario por Canal")
    st.dataframe(resumen, use_container_width=True)

    st.download_button(
        label="⬇️ Descargar Historial Completo",
        data=open(ARCHIVO_EXCEL, "rb"),
        file_name=ARCHIVO_EXCEL,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
except Exception as e:
    st.warning(f"No se pudo mostrar el historial: {e}")
# === ELIMINAR REGISTROS ===
st.markdown("---")
st.subheader("🗑️ Eliminar Registros")

col1, col2 = st.columns(2)

# Eliminar Negociación
with col1:
    st.markdown("### ❌ Negociación")
    if not df_neg.empty:
        id_neg = st.selectbox("Selecciona ID de negociación", df_neg["ID"], key="neg")
        if st.button("Eliminar Negociación"):
            df_neg = df_neg[df_neg["ID"] != id_neg]
            guardar_datos(df_neg, df_ing)
            st.success(f"Negociación con ID {id_neg} eliminada.")
    else:
        st.info("No hay negociaciones registradas.")

# Eliminar Ingreso
with col2:
    st.markdown("### ❌ Ingreso")
    if not df_ing.empty:
        index_ing = st.selectbox("Selecciona índice de ingreso", df_ing.index, key="ing")
        ingreso_info = df_ing.loc[index_ing]
        st.write(f"💰 Valor recibido: {ingreso_info['Valor Recibido']} COP")
        st.write(f"📅 Fecha: {ingreso_info['Fecha']} - 🕒 Hora: {ingreso_info['Hora Ingreso']}")

        if st.button("Eliminar Ingreso"):
            df_ing = df_ing.drop(index_ing).reset_index(drop=True)
            guardar_datos(df_neg, df_ing)
            st.success("Ingreso eliminado.")
    else:
        st.info("No hay ingresos registrados.")






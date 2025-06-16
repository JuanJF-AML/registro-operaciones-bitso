import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import locale

locale.setlocale(locale.LC_ALL, '')

ARCHIVO_EXCEL = "registro_operaciones_bitso.xlsx"
NEGOCIACIONES_SHEET = "Negociaciones"
INGRESOS_SHEET = "Ingresos"

# ========== FUNCIONES BASE ==========
def init_excel():
    if not Path(ARCHIVO_EXCEL).exists():
        with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl") as writer:
            pd.DataFrame(columns=[
                "Fecha", "Hora", "Monto USDT", "Tasa", "Esperado COP", "Estado", "ID", "Observacion"
            ]).to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)

            pd.DataFrame(columns=[
                "Fecha", "Hora Ingreso", "Valor Recibido", "Canal", "Asignado a", "Diferencia", "Demora (min)", "Observacion"
            ]).to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

def cargar_datos():
    df_neg = pd.read_excel(ARCHIVO_EXCEL, sheet_name=NEGOCIACIONES_SHEET)
    df_ing = pd.read_excel(ARCHIVO_EXCEL, sheet_name=INGRESOS_SHEET)
    return df_neg, df_ing

def guardar_datos(df_neg, df_ing):
    with pd.ExcelWriter(ARCHIVO_EXCEL, engine="openpyxl", mode="w") as writer:
        df_neg.to_excel(writer, sheet_name=NEGOCIACIONES_SHEET, index=False)
        df_ing.to_excel(writer, sheet_name=INGRESOS_SHEET, index=False)

# ========== INTERFAZ ==========
st.set_page_config(layout="centered", page_title="Operaciones Bitso")
init_excel()
df_neg, df_ing = cargar_datos()

pagina = st.sidebar.radio("Ir a:", ["📄 Registro de Operaciones", "📁 Historial y Reportes"])

# ========== REGISTRO ==========
if pagina == "📄 Registro de Operaciones":
    st.title("Registro de Operaciones Bitso")
    tabs = st.tabs(["📊 Operador", "📃 Tesorería"])

    with tabs[0]:
        st.subheader("📒 Registro del Operador")
        with st.form("form_operador"):
            fecha = st.date_input("Fecha de la operación", value=datetime.now().date())
            hora = st.text_input("Hora de negociación (HH:MM)")
            monto = st.number_input("Monto en USDT", min_value=0.0, step=1.0, format="%f")
            tasa = st.number_input("Tasa negociada", min_value=0.0, step=1.0, format="%f")
            obs = st.text_area("Observación (opcional)")
            submit_op = st.form_submit_button("Registrar Negociación")

            if submit_op:
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
                st.success(f"Operación registrada con ID: {id_op}")

    with tabs[1]:
        st.subheader("💳 Registro de Ingreso (Tesorería)")
        with st.form("form_tesoreria"):
            fecha_ing = st.date_input("Fecha del ingreso", value=datetime.now().date(), key="f")
            hora_ing = st.text_input("Hora del ingreso (HH:MM)")
            valor = st.number_input("Valor recibido en COP", min_value=0.0, step=100.0, format="%f")
            canal = st.selectbox("Canal", ["Coink", "Coopcentral"])
            obs = st.text_area("Observación (opcional)", key="obs2")

            opciones = df_neg[df_neg["Estado"] == "Pendiente"]
            opciones = opciones[opciones["Fecha"] == fecha_ing]
            seleccionadas = st.multiselect("Selecciona operaciones a asignar", opciones["ID"].tolist())

            submit_tes = st.form_submit_button("Registrar Ingreso")
            if submit_tes:
                valor_restante = valor
                asignaciones = []

                for op_id in seleccionadas:
                    idx = df_neg[df_neg["ID"] == op_id].index[0]
                    esperado = df_neg.at[idx, "Esperado COP"]

                    if valor_restante >= esperado:
                        df_neg.at[idx, "Estado"] = "Pagado"
                        valor_restante -= esperado
                        asignaciones.append(op_id)
                    elif valor_restante > 0:
                        df_neg.at[idx, "Esperado COP"] -= valor_restante
                        df_neg.at[idx, "Estado"] = "Parcial"
                        asignaciones.append(f"{op_id} (parcial)")
                        valor_restante = 0
                        break

                demora = None
                if asignaciones:
                    ref_id = seleccionadas[0]
                    fila = df_neg[df_neg["ID"] == ref_id].iloc[0]
                    dt_neg = datetime.strptime(f"{fila['Fecha']} {fila['Hora']}", "%Y-%m-%d %H:%M")
                    dt_ing = datetime.strptime(f"{fecha_ing} {hora_ing}", "%Y-%m-%d %H:%M")
                    demora = round((dt_ing - dt_neg).total_seconds() / 60, 2)

                diferencia = valor - sum(df_neg[df_neg["ID"].isin(seleccionadas)]["Esperado COP"])

                df_ing = pd.concat([df_ing, pd.DataFrame([{
                    "Fecha": fecha_ing,
                    "Hora Ingreso": hora_ing,
                    "Valor Recibido": valor,
                    "Canal": canal,
                    "Asignado a": ", ".join(asignaciones),
                    "Diferencia": diferencia,
                    "Demora (min)": demora,
                    "Observacion": obs
                }])], ignore_index=True)

                guardar_datos(df_neg, df_ing)
                st.success("Ingreso registrado con éxito")

# ========== HISTORIAL ==========
elif pagina == "📁 Historial y Reportes":
    st.title(":bar_chart: Resumen Diario")
    hoy = datetime.now().date()
    total_neg = df_neg[df_neg["Fecha"] == hoy]["Esperado COP"].sum()
    total_ing = df_ing[df_ing["Fecha"] == hoy]["Valor Recibido"].sum()
    pct = (total_ing / total_neg * 100) if total_neg > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("📉 Negociado Hoy (COP)", f"${int(total_neg):,}")
    col2.metric("💼 Ingresado Hoy", f"${int(total_ing):,}")
    col3.metric(":bookmark_tabs: % Cumplimiento", f"{pct:.1f}%")

    st.markdown("---")
    st.subheader(":file_folder: Historial Completo")
    tab1, tab2 = st.tabs(["Negociaciones", "Ingresos"])

    with tab1:
        df_show = df_neg.copy()
        df_show["Estado"] = df_show["Estado"].replace({
            "Pendiente": "❌ Pendiente",
            "Pagado": "✅ Pagado",
            "Parcial": "🔄 Parcial"
        })
        st.dataframe(df_show.sort_values("Fecha", ascending=False), use_container_width=True)

    with tab2:
        st.dataframe(df_ing.sort_values("Fecha", ascending=False), use_container_width=True)

    st.download_button(
        label="📄 Descargar Excel Completo",
        data=open(ARCHIVO_EXCEL, "rb"),
        file_name=ARCHIVO_EXCEL,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



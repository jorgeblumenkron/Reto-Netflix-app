import streamlit as st
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
from sqlalchemy import text
import json

# ==========================================
# CONEXIONES A BASES DE DATOS
# ==========================================

# 1. Firestore
key_dict = json.loads(st.secrets["textkey"])
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds, project=key_dict["project_id"])

# 2. PostgreSQL (Aiven)
conn = st.connection("postgresql", type="sql")

# ==========================================
# FUNCIONES CACHEABLES
# ==========================================

@st.cache_data
def load_movies():
    """Lee todos los registros de Firestore y los devuelve en un DataFrame"""
    movies_ref = list(db.collection(u'movies').stream())
    movies_dict = list(map(lambda x: x.to_dict(), movies_ref))
    # Si la colección está vacía, creamos un DataFrame con las columnas esperadas
    if not movies_dict:
        return pd.DataFrame(columns=['name', 'genre', 'director', 'company'])
    return pd.DataFrame(movies_dict)

movies_df = load_movies()

# ==========================================
# SIDEBAR E INTERFAZ PRINCIPAL
# ==========================================

st.sidebar.markdown("---")

# 1. Mostrar todos los filmes (Checkbox)
mostrar_todos = st.sidebar.checkbox("Mostrar todos los filmes")

if mostrar_todos:
    st.header("Netflix app")
    st.write("Done! (using st.cache)")
    st.subheader("Todos los filmes")
    st.dataframe(movies_df)

st.sidebar.markdown("---")

# 2. Buscar filmes por título (Text Input)
titulo_buscar = st.sidebar.text_input("Título del filme :")

if st.sidebar.button("Buscar filmes"):
    st.header("Netflix app")
    st.write("Done! (using st.cache)")
    # Búsqueda que "contenga" el texto, ignorando mayúsculas/minúsculas
    if not movies_df.empty and titulo_buscar:
        filtrado_titulo = movies_df[movies_df['name'].str.contains(titulo_buscar, case=False, na=False)]
        st.write(f"Total filmes mostrados : {len(filtrado_titulo)}")
        st.dataframe(filtrado_titulo)
    else:
        st.write("No hay filmes para mostrar.")

st.sidebar.markdown("---")

# 3. Filtrar por Director (Selectbox)
st.sidebar.write("Seleccionar Director")
if not movies_df.empty:
    lista_directores = movies_df['director'].dropna().unique()
else:
    lista_directores = []
    
director_seleccionado = st.sidebar.selectbox("Director", lista_directores, label_visibility="collapsed")

if st.sidebar.button("Filtrar director"):
    st.header("Netflix app")
    st.write("Done! (using st.cache)")
    if not movies_df.empty:
        filtrado_director = movies_df[movies_df['director'] == director_seleccionado]
        st.write(f"Total filmes : {len(filtrado_director)}")
        st.dataframe(filtrado_director)

st.sidebar.markdown("---")

# 4. Insertar nuevo filme (Firestore)
st.sidebar.subheader("Nuevo filme")
nuevo_nombre = st.sidebar.text_input("Name:")
nueva_compania = st.sidebar.text_input("Company:")
nuevo_director = st.sidebar.text_input("Director:")
nuevo_genero = st.sidebar.text_input("Genre:")

if st.sidebar.button("Crear nuevo filme"):
    if nuevo_nombre and nueva_compania and nuevo_director and nuevo_genero:
        doc_ref = db.collection("movies").document()
        doc_ref.set({
            "name": nuevo_nombre,
            "company": nueva_compania,
            "director": nuevo_director,
            "genre": nuevo_genero
        })
        st.sidebar.success("Filme insertado correctamente.")
        st.cache_data.clear() # Limpiar caché para ver el nuevo registro de inmediato
    else:
        st.sidebar.error("Llena todos los campos.")

st.sidebar.markdown("---")

# 5. Libro de Visitas: Registrar comentario (PostgreSQL)
st.sidebar.subheader("Libro de visitas")
email_visitante = st.sidebar.text_input("email :")
comentario_visitante = st.sidebar.text_input("Comentario :")

if st.sidebar.button("Registrar Visita"):
    if email_visitante and comentario_visitante:
        with conn.session as s:
            s.execute(
                text("INSERT INTO people (email, comment) VALUES (:email, :comment);"),
                {"email": email_visitante, "comment": comentario_visitante}
            )
            s.commit()
        st.sidebar.success("Visita registrada correctamente.")
    else:
        st.sidebar.error("Ingresa email y comentario.")

# 6. Libro de Visitas: Ver comentarios (PostgreSQL)
if st.sidebar.button("Ver visitas"):
    st.header("Netflix app")
    st.write("Done! (using st.cache)")
    st.subheader("Comentarios de visitantes")
    
    try:
        df_visitas = conn.query('SELECT * FROM people ORDER BY id ASC;', ttl="0m")
        count = 1
        for row in df_visitas.itertuples():
            st.markdown(f"**{count}.- {row.comment}** |  \n_{row.email}_")
            st.markdown("---")
            count += 1
    except Exception as e:
        st.error(f"Error al leer PostgreSQL: {e}")
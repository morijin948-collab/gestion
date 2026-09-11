"""
NAVARO-YACOUBA — Registre de gestion de fournitures scolaires (2026-2027)

Pour lancer l'application :
    1. pip install streamlit pandas
    2. streamlit run navaro_yacouba_app.py

Les données sont enregistrées dans deux fichiers créés à côté de ce script :
    - ny_admin.json   -> le compte administrateur
    - ny_data.json    -> les catégories et articles
Elles persistent donc réellement d'un lancement à l'autre.
"""

import json
import os
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# Chemins de stockage (à côté du script, pour que ça marche partout)
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_FILE = os.path.join(BASE_DIR, "ny_admin.json")
DATA_FILE = os.path.join(BASE_DIR, "ny_data.json")

EMPTY_DATA = {"categories": [], "articles": []}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, content):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)


def new_id():
    return uuid.uuid4().hex[:8]


def fmt_fcfa(n):
    return f"{n:,.0f}".replace(",", " ") + " FCFA"


def parse_number(raw):
    """Convertit un texte saisi (ex. '12', '1 500', '250,50') en nombre, ou None si invalide."""
    if raw is None:
        return None
    s = raw.strip().replace(" ", "").replace(",", ".")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Initialisation de l'état de session
# --------------------------------------------------------------------------
st.set_page_config(page_title="NAVARO-YACOUBA", page_icon="📒", layout="wide")

if "admin" not in st.session_state:
    st.session_state.admin = load_json(ADMIN_FILE, None)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = load_json(DATA_FILE, EMPTY_DATA)
if "view" not in st.session_state:
    st.session_state.view = "stats"


def persist_data():
    save_json(DATA_FILE, st.session_state.data)


# --------------------------------------------------------------------------
# En-tête commun
# --------------------------------------------------------------------------
def header():
    st.markdown("## 📒 NAVARO-YACOUBA")
    st.caption("Registre des fournitures scolaires · Année 2026 – 2027")


# --------------------------------------------------------------------------
# Écran : création du compte administrateur
# --------------------------------------------------------------------------
def signup_screen():
    header()
    st.markdown("### Créer le compte administrateur")
    st.write("Aucun compte n'existe encore sur cet ordinateur. Crée le tien pour commencer.")

    with st.form("signup_form", clear_on_submit=False):
        nom = st.text_input("Nom complet")
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        confirm = st.text_input("Confirmer le mot de passe", type="password")
        submitted = st.form_submit_button("Créer le compte", type="primary", use_container_width=True)

    if submitted:
        if not nom.strip() or not username.strip() or not password:
            st.error("Tous les champs sont obligatoires.")
        elif len(password) < 4:
            st.error("Le mot de passe doit contenir au moins 4 caractères.")
        elif password != confirm:
            st.error("La confirmation ne correspond pas au mot de passe.")
        else:
            account = {
                "nom": nom.strip(),
                "username": username.strip().lower(),
                "password": password,
                "cree_le": datetime.now().isoformat(timespec="seconds"),
            }
            save_json(ADMIN_FILE, account)
            st.session_state.admin = account
            st.session_state.logged_in = True
            st.success("Compte créé. Bienvenue !")
            st.rerun()


# --------------------------------------------------------------------------
# Écran : connexion
# --------------------------------------------------------------------------
def login_screen():
    header()
    st.markdown("### Connexion")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)

    if submitted:
        admin = st.session_state.admin
        if username.strip().lower() == admin["username"] and password == admin["password"]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")


# --------------------------------------------------------------------------
# Calculs
# --------------------------------------------------------------------------
def articles_df(category_id=None):
    articles = st.session_state.data["articles"]
    if category_id is not None:
        articles = [a for a in articles if a["category_id"] == category_id]
    if not articles:
        return pd.DataFrame(
            columns=["id", "nom", "quantite", "prix_achat", "prix_vente", "total_achat", "total_vente", "benefice"]
        )
    df = pd.DataFrame(articles)
    df["total_achat"] = df["quantite"] * df["prix_achat"]
    df["total_vente"] = df["quantite"] * df["prix_vente"]
    df["benefice"] = df["total_vente"] - df["total_achat"]
    return df


def category_totals(category_id):
    df = articles_df(category_id)
    return {
        "quantite": df["quantite"].sum() if not df.empty else 0,
        "achat": df["total_achat"].sum() if not df.empty else 0,
        "vente": df["total_vente"].sum() if not df.empty else 0,
        "benefice": df["benefice"].sum() if not df.empty else 0,
    }


# --------------------------------------------------------------------------
# Barre latérale : navigation + catégories
# --------------------------------------------------------------------------
def sidebar():
    st.sidebar.markdown(f"**{st.session_state.admin['nom']}**")
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.divider()

    if st.sidebar.button("📊 Statistiques", use_container_width=True,
                          type="primary" if st.session_state.view == "stats" else "secondary"):
        st.session_state.view = "stats"
        st.rerun()

    st.sidebar.caption("Catégories")

    categories = st.session_state.data["categories"]
    for cat in categories:
        cols = st.sidebar.columns([5, 1])
        is_active = st.session_state.view == cat["id"]
        if cols[0].button(cat["nom"], key=f"cat_{cat['id']}", use_container_width=True,
                           type="primary" if is_active else "secondary"):
            st.session_state.view = cat["id"]
            st.rerun()
        if cols[1].button("🗑", key=f"del_{cat['id']}"):
            st.session_state.data["categories"] = [c for c in categories if c["id"] != cat["id"]]
            st.session_state.data["articles"] = [
                a for a in st.session_state.data["articles"] if a["category_id"] != cat["id"]
            ]
            persist_data()
            if st.session_state.view == cat["id"]:
                st.session_state.view = "stats"
            st.rerun()

    with st.sidebar.form("new_category_form", clear_on_submit=True):
        new_cat_name = st.text_input("Nouvelle catégorie", label_visibility="collapsed",
                                      placeholder="Nom de la catégorie")
        if st.form_submit_button("➕ Ajouter la catégorie", use_container_width=True):
            if new_cat_name.strip():
                st.session_state.data["categories"].append({"id": new_id(), "nom": new_cat_name.strip()})
                persist_data()
                st.rerun()


# --------------------------------------------------------------------------
# Vue : catégorie (ajout d'articles + tableau)
# --------------------------------------------------------------------------
def category_view(category):
    st.markdown(f"### {category['nom']}")
    st.caption("Ajoute chaque article : les totaux et le bénéfice se calculent automatiquement.")

    with st.form(f"add_article_{category['id']}", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        nom = c1.text_input("Nom de l'article", placeholder="Ex. Cahier 192 pages")
        quantite_raw = c2.text_input("Quantité", placeholder="0")
        prix_achat_raw = c3.text_input("Prix d'achat (unité)", placeholder="0")
        prix_vente_raw = c4.text_input("Prix de vente (unité)", placeholder="0")

        if st.form_submit_button("➕ Ajouter l'article", type="primary"):
            quantite = parse_number(quantite_raw)
            prix_achat = parse_number(prix_achat_raw) or 0.0
            prix_vente = parse_number(prix_vente_raw) or 0.0

            if not nom.strip():
                st.warning("Indique un nom d'article.")
            elif quantite is None or quantite <= 0:
                st.warning("Indique une quantité valide, supérieure à 0 (ex. 12).")
            elif parse_number(prix_achat_raw) is None and prix_achat_raw.strip() != "":
                st.warning("Le prix d'achat n'est pas un nombre valide (ex. 250 ou 250.50).")
            elif parse_number(prix_vente_raw) is None and prix_vente_raw.strip() != "":
                st.warning("Le prix de vente n'est pas un nombre valide (ex. 350 ou 350.50).")
            else:
                st.session_state.data["articles"].append({
                    "id": new_id(),
                    "category_id": category["id"],
                    "nom": nom.strip(),
                    "quantite": quantite,
                    "prix_achat": prix_achat,
                    "prix_vente": prix_vente,
                })
                persist_data()
                st.rerun()

    df = articles_df(category["id"])

    if df.empty:
        st.info("Aucun article dans cette catégorie pour l'instant.")
        return

    st.divider()
    for _, row in df.iterrows():
        cols = st.columns([3, 1, 1.3, 1.3, 1.3, 1.3, 1.3, 0.6])
        cols[0].write(row["nom"])
        cols[1].write(f"{row['quantite']:.0f}")
        cols[2].write(fmt_fcfa(row["prix_achat"]))
        cols[3].write(fmt_fcfa(row["prix_vente"]))
        cols[4].write(fmt_fcfa(row["total_achat"]))
        cols[5].write(fmt_fcfa(row["total_vente"]))
        cols[6].write(fmt_fcfa(row["benefice"]))
        if cols[7].button("🗑", key=f"delart_{row['id']}"):
            st.session_state.data["articles"] = [
                a for a in st.session_state.data["articles"] if a["id"] != row["id"]
            ]
            persist_data()
            st.rerun()

    totals = category_totals(category["id"])
    st.divider()
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Quantité totale", f"{totals['quantite']:.0f}")
    t2.metric("Total achat", fmt_fcfa(totals["achat"]))
    t3.metric("Total vente", fmt_fcfa(totals["vente"]))
    t4.metric("Bénéfice", fmt_fcfa(totals["benefice"]))


# --------------------------------------------------------------------------
# Vue : statistiques globales
# --------------------------------------------------------------------------
def stats_view():
    st.markdown("### Tableau statistique")
    st.caption("Vue d'ensemble des achats, ventes et bénéfices, toutes catégories confondues.")

    categories = st.session_state.data["categories"]

    if not categories:
        st.info("Crée une catégorie dans le menu de gauche pour commencer ton registre.")
        return

    rows = []
    for cat in categories:
        t = category_totals(cat["id"])
        rows.append({
            "Catégorie": cat["nom"],
            "Quantité": t["quantite"],
            "Total achat": t["achat"],
            "Total vente": t["vente"],
            "Bénéfice": t["benefice"],
        })
    table = pd.DataFrame(rows)

    grand = {
        "quantite": table["Quantité"].sum(),
        "achat": table["Total achat"].sum(),
        "vente": table["Total vente"].sum(),
        "benefice": table["Bénéfice"].sum(),
    }

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Quantité totale", f"{grand['quantite']:.0f}")
    k2.metric("Montant d'achat total", fmt_fcfa(grand["achat"]))
    k3.metric("Montant de vente total", fmt_fcfa(grand["vente"]))
    k4.metric("Bénéfice total", fmt_fcfa(grand["benefice"]))

    st.divider()

    display_table = table.copy()
    for col in ["Total achat", "Total vente", "Bénéfice"]:
        display_table[col] = display_table[col].apply(fmt_fcfa)
    st.dataframe(display_table, use_container_width=True, hide_index=True)

    st.divider()
    st.caption("Achat, vente et bénéfice par catégorie")
    chart_df = table.set_index("Catégorie")[["Total achat", "Total vente", "Bénéfice"]]
    st.bar_chart(chart_df)


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------
def main():
    if st.session_state.admin is None:
        signup_screen()
        return

    if not st.session_state.logged_in:
        login_screen()
        return

    header()
    sidebar()

    view = st.session_state.view
    if view == "stats":
        stats_view()
    else:
        category = next((c for c in st.session_state.data["categories"] if c["id"] == view), None)
        if category is None:
            st.session_state.view = "stats"
            st.rerun()
        else:
            category_view(category)


if __name__ == "__main__":
    main()

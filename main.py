import streamlit as st
import pandas as pd
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions
import datetime
from collections import Counter

# Page configuration
st.set_page_config(
    page_title="User Dashboard",
    page_icon="👥",
    layout="wide"
)

def init_supabase():
    try:
        # Get credentials from Streamlit secrets
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        supabase = create_client(
            supabase_url,
            supabase_key,
            options=SyncClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            )
        )
        return supabase
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {str(e)}")
        return None

def fetch_user_data(supabase_client):
    try:
        if supabase_client is None:
            st.error('No supabase client connected')
            return

        admin_auth_client = supabase_client.auth.admin
        response = admin_auth_client.list_users()

        # NOTE; response is a list with user objects containing metadata.
        # st.write(response)

        if response:
            # Convert User objects to dictionaries
            user_data = []
            for user in response:
                user_dict = {
                    'user_id': user.id,
                    'display_name': user.user_metadata.get('full_name', 'N/A') if user.user_metadata else 'N/A',
                    'email': user.email,
                    'created_at': user.created_at,
                    'last_sign_in_at': user.last_sign_in_at
                }
                user_data.append(user_dict)

            df = pd.DataFrame(user_data)
            return df
        else:
            st.info("No user data found")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return

def format_overview_dataframe(df):
    if df.empty:
        return df

    display_df = df.copy()

    display_df = display_df.drop('user_id', axis = 1)

    datetime_columns = ['created_at', 'last_sign_in_at']
    for col in datetime_columns:
        if col in display_df.columns:
            # Convert to datetime and format
            display_df[col] = pd.to_datetime(display_df[col])
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

    column_mapping = {
        'display_name': 'Nome',
        'email': 'Email',
        'created_at': 'Primo Accesso',
        'last_sign_in_at': 'Ultimo Accesso'
    }

    display_df = display_df.rename(columns=column_mapping)

    return display_df

def fetch_count_data_by_user(supabase_client):
    response = supabase_client.table("fatture_emesse").select("user_id").execute()
    user_ids = [row["user_id"] for row in response.data if row.get("user_id")]
    emesse_counts = Counter(user_ids)

    response = supabase_client.table("fatture_ricevute").select("user_id").execute()
    user_ids = [row["user_id"] for row in response.data if row.get("user_id")]
    ricevute_counts = Counter(user_ids)

    response = supabase_client.table("movimenti_attivi").select("user_id").execute()
    user_ids = [row["user_id"] for row in response.data if row.get("user_id")]
    attivi_counts = Counter(user_ids)

    response = supabase_client.table("movimenti_passivi").select("user_id").execute()
    user_ids = [row["user_id"] for row in response.data if row.get("user_id")]
    passivi_counts = Counter(user_ids)

    return emesse_counts, ricevute_counts, attivi_counts, passivi_counts

def merge_user_counts(df, emesse_counts, ricevute_counts, attivi_counts, passivi_counts):
    df = df[["user_id", "email"]].copy()

    df["totale_fatture_emesse"]   = df["user_id"].map(emesse_counts).fillna(0).astype(int)
    df["totale_fatture_ricevute"] = df["user_id"].map(ricevute_counts).fillna(0).astype(int)
    df["totale_movimenti_attivi"]   = df["user_id"].map(attivi_counts).fillna(0).astype(int)
    df["totale_movimenti_passivi"]  = df["user_id"].map(passivi_counts).fillna(0).astype(int)

    df = df[["email", "totale_fatture_emesse", "totale_fatture_ricevute", "totale_movimenti_attivi", "totale_movimenti_passivi"]]

    return df

def main():
    supabase = init_supabase()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        refresh_button = st.button("Mostra Dati", use_container_width=True)

    if refresh_button:
        with st.spinner("Carico..."):
            df = fetch_user_data(supabase)
            emesse_counts, ricevute_counts, attivi_counts, passivi_counts = fetch_count_data_by_user(supabase)

            if not df.empty:
                st.caption(f"Ultimo caricamento: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                display_df = format_overview_dataframe(df)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Utenti Totali", len(display_df))
                with col2:
                    if 'Ultimo Accesso' in display_df.columns:
                        recent_signins = len(display_df[pd.to_datetime(display_df['Ultimo Accesso']) > datetime.datetime.now() - datetime.timedelta(days=7)])
                        st.metric("Attivi Questa Settimana", recent_signins)
                with col3:
                    if 'Primo Accesso' in display_df.columns:
                        new_users = len(display_df[pd.to_datetime(display_df['Primo Accesso']) > datetime.datetime.now() - datetime.timedelta(days=30)])
                        st.metric("Nuovi Utenti (30 giorni)", new_users)

                df_with_counts = merge_user_counts(df, emesse_counts, ricevute_counts, attivi_counts, passivi_counts)
                df_joined = display_df.merge(df_with_counts, left_on='Email', right_on='email', how='outer')
                st.dataframe(
                    df_joined.drop('email', axis = 1),
                    use_container_width=True,
                    hide_index=True
                )

                with st.expander("Vecchia visualizzazione"):
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.dataframe(
                        df_with_counts,
                        use_container_width=True,
                        hide_index=True
                    )

            else:
                st.info("Nessun dato disponibile.")
    else:
        st.info("Cliccare per ottenere i dati dal database.")

if __name__ == "__main__":
    main()
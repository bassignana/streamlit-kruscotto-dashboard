import streamlit as st
import pandas as pd
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions
import datetime

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
        ####################################
        if response:
            # Convert User objects to dictionaries
            user_data = []
            for user in response:
                user_dict = {
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

def format_dataframe(df):
    if df.empty:
        return df

    display_df = df.copy()

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
##############################################################
def main():
    supabase = init_supabase()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        refresh_button = st.button("Mostra Dati", use_container_width=True)

    if refresh_button:
        with st.spinner("Carico..."):
            df = fetch_user_data(supabase)

            if not df.empty:
                st.caption(f"Ultimo caricamento: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                display_df = format_dataframe(df)

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

                st.markdown("### User Data")

                # Display the dataframe
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nessun dato disponibile.")
    else:
        st.info("Cliccare per ottenere i dati dal database.")

if __name__ == "__main__":
    main()
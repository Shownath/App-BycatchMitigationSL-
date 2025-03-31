import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

st.set_page_config(
    page_title="Bycatch Mitigation Analysis",
    page_icon="🐬",
    layout="wide"
)


st.title("Bycatch Mitigation Analysis - Sri Lanka")

st.markdown("""
### Overview
This app analyzes fishing data to compare the effectiveness of different net modifications 
(**Control, Subsurface, and Illuminated**) in reducing bycatch in Sri Lankan fisheries.

### Project Details
This study is conducted under the **Marine Megafauna Bycatch Mitigation  Pilot Project**, led by 
**Blue Resources Trust** under the **Fisheries and Policy Programme**, in collaboration with 
**Oregon State University, USA**.
""")

@st.cache_data
def load_data():
    """Load data from Google Sheets"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
       
        creds = ServiceAccountCredentials.from_json_keyfile_name("secret.json", scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Data Sheet ByCatch Mitigation SL")
        worksheet_list = spreadsheet.worksheets()
        sheet_names = [sheet.title for sheet in worksheet_list]
        boat_sheets = [name for name in sheet_names if name.lower().startswith('boat')]

        df_list = []
        for sheet_name in boat_sheets:
            sheet = spreadsheet.worksheet(sheet_name)
            data = sheet.get_all_values()
            
            # Ensure column names are unique
            headers = data[0]
            if len(headers) != len(set(headers)):
                seen = {}
                unique_headers = []
                for i, h in enumerate(headers):
                    if h in seen:
                        unique_headers.append(f"{h}_{i}")
                    else:
                        unique_headers.append(h)
                        seen[h] = True
                headers = unique_headers
            
            df = pd.DataFrame(data[1:], columns=headers)
            df["Boat Sheet"] = sheet_name
            df_list.append(df)
        

        final_df = pd.concat(df_list, ignore_index=True)
        
       
        final_df["Date"] = pd.to_datetime(final_df["Date"], errors='coerce')
        final_df = final_df.sort_values(by="Date", ascending=True).reset_index(drop=True)
        
       
        bycatch_species = ['Manta', 'Turtle', 'Dolphin', 'Shark', 'Bird']
        target_species = ['Yellowfin', 'Skipjack','Billfish']
        all_species = target_species + bycatch_species
        
        for column in all_species:
            final_df[column] = pd.to_numeric(final_df[column], errors='coerce').fillna(0)
        
      
        final_df['Total_Bycatch'] = final_df[bycatch_species].sum(axis=1)
        final_df['Total_Target'] = final_df[target_species].sum(axis=1)
        
        return final_df, all_species, bycatch_species, target_species
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None

##upload data opion
def upload_data():
    uploaded_file = st.file_uploader("Upload your bycatch data CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            final_df = pd.read_csv(uploaded_file)
            
           
            if "Date" in final_df.columns:
                final_df["Date"] = pd.to_datetime(final_df["Date"], errors='coerce')
                final_df = final_df.sort_values(by="Date", ascending=True).reset_index(drop=True)
            
           
            bycatch_species = [ 'Manta', 'Turtle', 'Dolphin', 'Shark', 'Bird']
            target_species = ['Yellowfin', 'Skipjack','Billfish']
            all_species = target_species + bycatch_species
            
          
            for column in all_species:
                if column in final_df.columns:
                    final_df[column] = pd.to_numeric(final_df[column], errors='coerce').fillna(0)
            
           
            existing_bycatch = [col for col in bycatch_species if col in final_df.columns]
            existing_target = [col for col in target_species if col in final_df.columns]
            
            if existing_bycatch:
                final_df['Total_Bycatch'] = final_df[existing_bycatch].sum(axis=1)
            if existing_target:
                final_df['Total_Target'] = final_df[existing_target].sum(axis=1)
            
            return final_df, all_species, bycatch_species, target_species
        except Exception as e:
            st.error(f"Error processing uploaded file: {e}")
            return None, None, None, None
    return None, None, None, None

# Sidebar for data source selection
st.sidebar.header("Data Source")
data_source = st.sidebar.radio(
    "Select Data Source:",
    ["Google Sheets", "Upload CSV"]
)

# Load data based on selection
if data_source == "Google Sheets":
    df, all_species, bycatch_species, target_species = load_data()
else:
    df, all_species, bycatch_species, target_species = upload_data()

# Continue only if data is loaded
if df is not None:
    st.sidebar.header("Filter Options")
    
    # Date range selector
    st.sidebar.subheader("Date Range")
    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Select date range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Boat selector
    st.sidebar.subheader("Boat Selection")
    boats = ["All Boats"] + list(df["Boat Sheet"].unique())
    selected_boats = st.sidebar.multiselect(
        "Select boats to include:",
        boats,
        default=["All Boats"]
    )
    
    # Panel Type selector
    st.sidebar.subheader("Panel Type")
    panel_types = list(df["Panel Type"].unique())
    selected_panels = st.sidebar.multiselect(
        "Select panel types to analyze:",
        panel_types,
        default=panel_types
    )
    
    # Filter data based on selections
    filtered_df = df.copy()
    
    # Apply date filter
    filtered_df = filtered_df[(filtered_df["Date"].dt.date >= start_date) & 
                              (filtered_df["Date"].dt.date <= end_date)]
    
    # Apply boat filter
    if "All Boats" not in selected_boats:
        filtered_df = filtered_df[filtered_df["Boat Sheet"].isin(selected_boats)]
    
    # Apply panel type filter
    filtered_df = filtered_df[filtered_df["Panel Type"].isin(selected_panels)]
    
    # Check if there's data after filtering
    if filtered_df.empty:
        st.warning("No data available with the selected filters. Please adjust your selections.")
    else:
        # Display dataset overview
        st.header("Dataset Overview")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Records", filtered_df.shape[0])
            st.metric("Date Range", f"{filtered_df['Date'].min().date()} to {filtered_df['Date'].max().date()}")
        
        with col2:
            total_bycatch = filtered_df["Total_Bycatch"].sum()
            total_target = filtered_df["Total_Target"].sum()
            st.metric("Total Bycatch", f"{int(total_bycatch)}")
            st.metric("Total Target Catch", f"{int(total_target)}")
        
        # Summary statistics by panel type
        st.header("Panel Type Comparison")
        panel_stats = filtered_df.groupby("Panel Type")[bycatch_species + ["Total_Bycatch", "Total_Target"]].sum()
        panel_stats["Bycatch_Ratio"] = panel_stats["Total_Bycatch"] / panel_stats["Total_Target"]
        panel_stats = panel_stats.reset_index()
        
        # Visualization tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Total Bycatch", "Species Breakdown", "Bycatch Ratio", "Heatmap"])
        
        with tab1:
            # Bar chart of total bycatch by panel type
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(x="Panel Type", y="Total_Bycatch", data=panel_stats, ax=ax)
            ax.set_title("Total Bycatch by Panel Type")
            ax.set_ylabel("Count")
            st.pyplot(fig)
            
            # Display the data table
            st.subheader("Total Bycatch Data")
            st.dataframe(panel_stats[["Panel Type", "Total_Bycatch"]])
        
        with tab2:
            # Species-specific bycatch
            st.subheader("Bycatch by Species")
            species_selection = st.multiselect(
                "Select species to display:",
                bycatch_species,
                default=bycatch_species
            )
            
            if species_selection:
                # Melt the dataframe for species-specific plotting
                melted_data = pd.melt(
                    filtered_df, 
                    id_vars=["Panel Type"], 
                    value_vars=species_selection,
                    var_name="Species", 
                    value_name="Count"
                )
                
                # Group by Panel Type and Species to get total counts
                species_counts = melted_data.groupby(["Panel Type", "Species"])["Count"].sum().reset_index()
                
                # Create the plot
                fig, ax = plt.subplots(figsize=(12, 7))
                sns.barplot(x="Species", y="Count", hue="Panel Type", data=species_counts, ax=ax)
                ax.set_title("Bycatch by Species and Panel Type")
                ax.set_xlabel("Species")
                ax.set_ylabel("Count")
                plt.xticks(rotation=45)
                plt.legend(title="Panel Type")
                plt.tight_layout()
                st.pyplot(fig)
                
                # Display the data table
                st.subheader("Species Bycatch Data")
                st.dataframe(species_counts)
        
        with tab3:
            # Bycatch ratio (bycatch per target fish)
            st.subheader("Bycatch to Target Catch Ratio")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(x="Panel Type", y="Bycatch_Ratio", data=panel_stats, ax=ax)
            ax.set_title("Bycatch Ratio (Bycatch / Target Catch) by Panel Type")
            ax.set_ylabel("Ratio")
            st.pyplot(fig)
            
            # Display the data table
            st.subheader("Bycatch Ratio Data")
            st.dataframe(panel_stats[["Panel Type", "Bycatch_Ratio"]].round(4))
        
        with tab4:
            # Heatmap
            st.subheader("Bycatch Heatmap")
            
            # Prepare data for heatmap (species x panel type)
            heatmap_data = panel_stats.set_index("Panel Type")[bycatch_species].T
            
            # Create the heatmap
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(heatmap_data, annot=True, cmap="YlOrRd", fmt=".0f", ax=ax)
            ax.set_title("Bycatch Count by Species and Panel Type")
            ax.set_xlabel("Panel Type")
            ax.set_ylabel("Species")
            plt.tight_layout()
            st.pyplot(fig)
        
        # # Statistical Analysis
        # st.header("Statistical Analysis")
        
        # tab_stats1, tab_stats2 = st.tabs(["Reduction Effectiveness", "Temporal Analysis"])
        
        # with tab_stats1:
        #     # Calculate bycatch reduction percentages relative to control
        #     st.subheader("Bycatch Reduction Effectiveness")
            
        #     # Group by date and panel type to treat each fishing day as an independent observation
        #     daily_stats = filtered_df.groupby(["Date", "Panel Type"])["Total_Bycatch"].sum().reset_index()
            
        #     # Calculate descriptive statistics by panel type
        #     panel_desc = daily_stats.groupby("Panel Type")["Total_Bycatch"].agg(["mean", "median", "std", "count"]).reset_index()
            
        #     # Find the control panel's mean if it exists
        #     if "Control" in panel_desc["Panel Type"].values:
        #         control_mean = panel_desc.loc[panel_desc["Panel Type"] == "Control", "mean"].values[0]
                
        #         # Calculate reduction percentages
        #         panel_desc["reduction_pct"] = ((control_mean - panel_desc["mean"]) / control_mean * 100)
                
        #         # Create a bar chart of reduction percentages
        #         non_control = panel_desc[panel_desc["Panel Type"] != "Control"]
                
        #         if not non_control.empty:
        #             fig, ax = plt.subplots(figsize=(10, 6))
        #             sns.barplot(x="Panel Type", y="reduction_pct", data=non_control, ax=ax)
        #             ax.set_title("Bycatch Reduction Percentage Compared to Control")
        #             ax.set_ylabel("Reduction Percentage (%)")
        #             ax.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        #             st.pyplot(fig)
            
        #     # Display the statistics table
        #     st.subheader("Descriptive Statistics by Panel Type")
        #     st.dataframe(panel_desc.round(2))
        
        # with tab_stats2:
        #     # Temporal analysis
        #     st.subheader("Bycatch Over Time")
            
        #     # Group by date and panel type
        #     time_series = filtered_df.groupby(["Date", "Panel Type"])["Total_Bycatch"].sum().reset_index()
            
        #     # Plot time series
        #     fig, ax = plt.subplots(figsize=(12, 6))
        #     sns.lineplot(x="Date", y="Total_Bycatch", hue="Panel Type", data=time_series, ax=ax)
        #     ax.set_title("Bycatch Over Time by Panel Type")
        #     ax.set_xlabel("Date")
        #     ax.set_ylabel("Total Bycatch")
        #     plt.xticks(rotation=45)
        #     plt.tight_layout()
        #     st.pyplot(fig)
        
        # # Data explorer section
        # st.header("Data Explorer")
        
        # # Allow users to select columns to view
        # cols_to_show = st.multiselect(
        #     "Select columns to display:",
        #     df.columns,
        #     default=["Date", "Boat Sheet", "Panel Type", "Total_Bycatch", "Total_Target"] + bycatch_species
        # )
        
        # # Show the filtered data with selected columns
        # if cols_to_show:
        #     st.dataframe(filtered_df[cols_to_show])
        
        # # Option to download filtered data
        # csv = filtered_df.to_csv(index=False).encode('utf-8')
        # st.download_button(
        #     "Download Filtered Data as CSV",
        #     csv,
        #     "bycatch_filtered_data.csv",
        #     "text/csv",
        #     key='download-csv'
        # )
        
    
        

else:
    st.info("Please select a data source to get started.")

# Footer with credits
st.markdown("---")
st.markdown("MarineMegafauna Bycatch Mitigation Srilanka | Blue resources Trust | Oregon State University, USA")
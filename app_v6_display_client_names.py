import streamlit as st
import gspread
import pandas as pd
from google.oauth2 import service_account
from getfilelistpy import getfilelist

### Google Drive API authentication (LOCAL) ########################################################################
# Authenticate Google Drive API
# Authenticate Google Sheets API
#creds = service_account.Credentials.from_service_account_file(
#    'C:/Users/HP/Downloads/credentials.json',
#    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
#)
#############################################################################################################

### Google Drive API authentication (STREAMLIT SHARE)########################################################################
# Authenticate Google Drive API
# Authenticate Google Sheets API
raw_creds = st.secrets["raw_creds"]
json_creds = json.loads(raw_creds)

creds = service_account.Credentials.from_service_account_info(
    json_creds,
    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
)
#############################################################################################################

# Authorize Google Sheets API
client = gspread.authorize(creds)

# Load the table of client login credentials
sheet = client.open('Growth list manager login credentials').sheet1

# Define a function to load the client credentials and URLs of the folder with their lists
def login(name, password):
    data = sheet.get_all_records()
    for row in data:
        if row['Name'] == name and row['Password'] == password:
            return row['Folder_URL']
    return None

# Define a function to get files in a folder using getfilelist
def get_files_in_nested_folders(folder_url):
    resource = {
        "service_account":creds,
        "id": folder_url.split('/')[-1],
        "fields": "files(name,id,webViewLink)",
    }
    res = getfilelist.GetFileList(resource)
    file_records = []

    # retrieve each file's name, link, id and the last foldertree (id of the folder that it is in)
    for file_list_item in res['fileList']:
        file_data = file_list_item.get('files', [])
        folder_tree = file_list_item.get('folderTree', [])  # Retrieve the folderTree data

        for file_item in file_data:
            name = file_item.get('name', None)
            id = file_item.get('id', None)
            webViewLink = file_item.get('webViewLink', None)

            # Include folderTree in each item
            file_records.append({
                'name': name,
                'id': id,
                'webViewLink': webViewLink,
                'folderTree': folder_tree  # Add folderTree data to each item
            })

    # Preserve only the second foldertree value (the name of the client folder id)
    for record in file_records:
        folder_tree = record['folderTree']
        if len(folder_tree) > 1:
            record['folderTree'] = folder_tree[-1]
        else:
            record['folderTree'] = None

    ### Create a dataframe to store the info about each file
    files = pd.DataFrame(file_records, columns=["name", "id", "webViewLink", "folderTree"])

    ########################################################################################################

    # get the names of folders corresponding to their foldertree codes
    folder_tree_names = pd.DataFrame(res['folderTree'])
    # rename for merging
    folder_tree_names = folder_tree_names.rename(columns={"folders": "folderTree"})

    # merge them to the records
    files = files.merge(folder_tree_names, on='folderTree', how='left')

    # drop files wich are not nested in a folder with the name of a client
    files = files.dropna(subset = ['names'])
    
    return files



# Define the app
def main():
    st.title("Growth List Manager")
    st.write("""Welcome to the Connected Circles Growth List Manager. Log in to view your growth lists""")
    
    st.title('Login')
    name = st.text_input('Name')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        folder_url = login(name, password)
        if folder_url:
            st.success('Login Successful!')
            # Display clickable URLs to files in the folder
            files = get_files_in_nested_folders(folder_url)
            if not files.empty:
                grouped = files.groupby('names')
                for name, group in grouped:
                    st.subheader(name)
                    for idx, row in group.iterrows():
                        st.markdown(f"**[{row['name']}]({row['webViewLink']})**")

            else:
                st.markdown("No files found in the folder.")
        else:
            st.error('Invalid credentials')

# Run the app
if __name__ == '__main__':
    main()

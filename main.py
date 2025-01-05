import streamlit as st
import requests
from PIL import Image
import io
import streamlit_cropper

event_id = "BRF25"

# Define the backend API endpoint
BACKEND_API_URL = "https://ticket-web-service-6kelgrpcxq-uc.a.run.app/"
VENDOR_AFFILIATION_API_URL = "https://www.renfairdata.org/api/vendors?fair=brevard&year=2025"
ENTERTAINMENT_AFFILIATION_API_URL = "https://www.renfairdata.org/api/acts?fair=brevard&year=2025"
BULK_ENTRY_API_URL = "http://your-backend-api-url.com/bulk_submit"

st.set_page_config(menu_items=None)
st.set_page_config(page_title="BRF Badge Creator")
st.set_page_config(page_icon="👑")

# Function to fetch affiliations from API
def fetch_affiliations(role:str):
    response = None
    try:
        if role == "Vendor":    
            response = requests.get(VENDOR_AFFILIATION_API_URL)
        elif role == "Entertainment":
            response = requests.get(ENTERTAINMENT_AFFILIATION_API_URL)
        else:
            data = ["Admin", "Bar Staff", "Security"]

        if response != None and response.status_code == 200:
            data = response.json()
            return [item["Name"] for item in data]
        else:
            return data
    except Exception as e:
        st.error(f"An error occurred while fetching affiliations: {e}")
        return []

# Page 1: Single Entry
def single_entry():
    # Display the logo at the top of the page
    logo_url = "https://brevardrenaissancefair.com/wp-content/uploads/2023/03/BRF-Logo-2025-10th-Aniv-400px.png"
    try:
        response = requests.get(logo_url)
        if response.status_code == 200:
            logo_image = Image.open(io.BytesIO(response.content))
            st.image(logo_image, width=200)
        else:
            st.error("Failed to load logo image")
    except Exception as e:
        st.error(f"Error loading logo: {e}")
    st.title("Badge Creator")
    # Check for person_id in URL parameters
    params = st.query_params

    st.session_state.first_name = ""
    st.session_state.last_name = ""
    st.session_state.affiliation = ""
    st.session_state.role = "Vendor"
    existing_data = None

    if "person_id" in params:
        try:
            # Call API to get existing badge data
            person_id = params["person_id"]
            response = requests.get(f"http://localhost:8080/person/{person_id}")
            
            if response.status_code == 200:
                
                existing_data = response.json()
                # Store the data in session state to prefill fields
                st.session_state.first_name = existing_data.get("first_name", "")
                st.session_state.last_name = existing_data.get("last_name", "")
                # Find the badge with matching event_id
                matching_badge = next((badge for badge in existing_data.get("badges", []) 
                                    if badge.get("event_id") == event_id), {})
                st.session_state.affiliation = matching_badge.get("affiliation", "")
                st.session_state.role = matching_badge.get("role", "Staff")
              
            else:
                st.error("Failed to fetch existing badge data")
        except Exception as e:
            st.error(f"Error fetching badge data: {e}")

    # Input fields
    first_name = st.text_input("First Name", value=st.session_state.first_name if st.session_state.first_name else "")
    last_name = st.text_input("Last Name", value=st.session_state.last_name if st.session_state.last_name else "")
    # Dropdown for role selection (placed before affiliation to control visibility)
    role = st.selectbox("Select a Role", ["Staff", "Vendor", "Entertainment", "Royal Family", "Season Pass"], index=["Staff", "Vendor", "Entertainment", "Royal Family", "Season Pass"].index(st.session_state.role if st.session_state.role else "Staff"))
    # Update affiliations when role changes
    if "previous_role" not in st.session_state:
        st.session_state.previous_role = role
    
    if st.session_state.previous_role != role:
        # Clear any existing affiliation value
        if "affiliation" in st.session_state:
            del st.session_state.affiliation
        st.session_state.previous_role = role
        # Force a rerun to update the UI
        st.rerun()

    # Only show affiliation fields if a role is selected and it's not Royal Family or Season Pass
    if role not in ["Royal Family", "Season Pass"] or role == "Select a Role":
        # Autocomplete for affiliation 
        affiliations = fetch_affiliations(role)
        
        if affiliations:
            selected_affiliation = st.selectbox("Select an Affiliation", ["(Other)"] + affiliations)
            if selected_affiliation != "(Other)":
                affiliation = selected_affiliation
            else:
                affiliation = st.text_input("Other Affiliation", value=st.session_state.affiliation if st.session_state.affiliation else "")
    else:
        # Set default values when hidden
        affiliation = st.session_state.affiliation if st.session_state.affiliation else ""
        role = role

    # File uploader for photo
    photo = st.file_uploader("Upload a Photo", type=["jpg", "jpeg", "png"])

    cropped_image = None

    if photo:
        # Preview the uploaded photo
        image = Image.open(photo)
        st.image(image, caption="Uploaded Photo", width=200)

        # Add cropping functionality
        st.write("Crop your photo below:")
        cropped_image = streamlit_cropper.st_cropper(
            image, aspect_ratio=(1, 1), box_color="#FF0000"
        )

        if cropped_image:
            st.image(cropped_image, caption="Cropped Photo", width=200)

    # Submit button
    if st.button("Submit"):
        if not first_name or not last_name or not affiliation or not cropped_image:
            st.error("Please fill in all fields and upload a cropped photo.")
        else:
            # Convert cropped image to bytes
            cropped_image_bytes = io.BytesIO()
            cropped_image.save(cropped_image_bytes, format="PNG")

            # Prepare the payload
            if existing_data != None:
                payload = {
                    "person_id": person_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "affiliation": affiliation,
                    "role": role,
                    "event_id": event_id
                }
            else:
                payload = {
                    "person_id": "None",
                    "first_name": first_name,
                    "last_name": last_name,
                    "affiliation": affiliation,
                    "role": role,
                    "event_id": event_id
                }

            # Prepare the file for upload
            files = {"photo": cropped_image_bytes.getvalue()}
            
        

            try:
                # Send the request to the backend API
                response = requests.post(BACKEND_API_URL + "badge", data=payload, files=files)

                if response.status_code == 200:
                    st.success("Badge created successfully!")
                else:
                    st.error(f"Failed to submit entry: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# Page 2: Bulk Entry
def bulk_entry():
    st.title("Bulk Entry Form")

    # Autocomplete for affiliation
    affiliations = fetch_affiliations()
    affiliation = st.text_input("Affiliation", value="")
    if affiliations:
        selected_affiliation = st.selectbox("Select an Affiliation", ["(Other)"] + affiliations)
        if selected_affiliation != "(Other)":
            affiliation = selected_affiliation

    # Bulk entry table
    st.write("Enter details for multiple people below:")

    # Initialize session state for table data
    if "bulk_data" not in st.session_state:
        st.session_state.bulk_data = [{"first_name": "", "last_name": "", "email": ""}]

    # Add rows button
    if st.button("Add Row"):
        st.session_state.bulk_data.append({"first_name": "", "last_name": "", "email": ""})

    # Display table for data entry
    for i, row in enumerate(st.session_state.bulk_data):
        cols = st.columns(3)
        row["first_name"] = cols[0].text_input(f"First Name {i+1}", value=row["first_name"])
        row["last_name"] = cols[1].text_input(f"Last Name {i+1}", value=row["last_name"])
        row["email"] = cols[2].text_input(f"Email {i+1}", value=row["email"])

    # Submit button
    if st.button("Submit Bulk Data"):
        if not affiliation:
            st.error("Please provide an affiliation.")
        else:
            entries = [
                {**row, "affiliation": affiliation}
                for row in st.session_state.bulk_data
                if row["first_name"] and row["last_name"] and row["email"]
            ]

            if not entries:
                st.error("Please provide at least one valid entry.")
                return

            # Send the bulk data to the backend API
            try:
                response = requests.post(BULK_ENTRY_API_URL , json={"entries": entries})

                if response.status_code == 200:
                    st.success("Bulk data submitted successfully!")
                else:
                    st.error(f"Failed to submit bulk data: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# Main function to handle navigation
def main():
  #  st.sidebar.title("Navigation")
  #  page = st.sidebar.radio("Go to", ["Single Entry", "Bulk Entry"])

   # if page == "Single Entry":
        single_entry()
   # elif page == "Bulk Entry":
   #s     bulk_entry()

if __name__ == "__main__":
    main()

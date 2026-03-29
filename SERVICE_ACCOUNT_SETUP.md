# Google Service Account Setup for SWPPP Drive Upload

## Why This Approach
A Service Account is a robot Google account that never expires and never needs re-authorization.
It uploads files directly to your Drive folder without any OAuth flow or browser redirects.

## Steps (takes ~3 minutes in your browser)

### Step 1 — Go to Google Cloud Console
Open: https://console.cloud.google.com/iam-admin/serviceaccounts?project=swppp-inspection-workflow

(You may need to enable 2SV first if prompted)

### Step 2 — Create a Service Account
1. Click **+ CREATE SERVICE ACCOUNT**
2. Name it: `swppp-drive-uploader`
3. Description: `SWPPP inspection report Drive uploader`
4. Click **CREATE AND CONTINUE**
5. Skip the optional role/permissions steps — click **DONE**

### Step 3 — Create and Download a JSON Key
1. Click on the service account you just created
2. Go to the **KEYS** tab
3. Click **ADD KEY** → **Create new key**
4. Choose **JSON** format
5. Click **CREATE** — a JSON file will download to your Mac

### Step 4 — Share Your Drive Folder with the Service Account
1. Open the downloaded JSON file in a text editor
2. Find the `client_email` field — it looks like:
   `swppp-drive-uploader@swppp-inspection-workflow.iam.gserviceaccount.com`
3. Go to Google Drive: https://drive.google.com
4. Find the folder **"Manor House SWPPP Inspection Reports"**
5. Right-click → **Share**
6. Paste the service account email address
7. Set permission to **Editor**
8. Click **Send** (ignore the warning about sharing with a non-Google account)

### Step 5 — Send the JSON Key File
Upload the downloaded JSON key file here in this Manus chat.
I'll install it and update the app to use it — Drive uploads will work permanently after that.

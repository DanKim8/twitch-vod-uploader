from google_auth_oauthlib.flow import InstalledAppFlow
import json

# Use the 'upload' scope so you have permission to post videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    # 1. Start the flow using your downloaded secrets file
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json', 
        scopes=SCOPES
    )

    # 2. This will open your web browser
    credentials = flow.run_local_server(port=0)

    # 3. Save the credentials (including the REFRESH TOKEN) to a file
    with open('token.json', 'w') as token_file:
        token_file.write(credentials.to_json())
    
    print("✅ token.json has been created successfully!")

if __name__ == "__main__":
    main()
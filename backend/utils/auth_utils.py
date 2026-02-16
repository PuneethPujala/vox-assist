import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
import logging
from pathlib import Path

# Setup Path
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Initialize Firebase Admin
cred_filename = os.getenv("FIREBASE_CREDENTIALS_PATH", "service-account-key.json")

# Handle "backend/" prefix if present in env var to avoid duplication
if cred_filename.startswith("backend/") or cred_filename.startswith("backend\\"):
    cred_filename = os.path.basename(cred_filename)

cred_path = backend_dir / cred_filename

if not firebase_admin._apps:
    try:
        # Convert to string for firebase admin
        cred_path_str = str(cred_path)
        if cred_path.exists():
            cred = credentials.Certificate(cred_path_str)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin initialized with credentials at {cred_path_str}")
        else:
            logger.warning(f"Firebase credentials not found at {cred_path_str}. Auth verification will fail.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify the Firebase ID token.
    """
    token = credentials.credentials
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_uid(token_data: dict = Depends(verify_token)):
    return token_data.get("uid")

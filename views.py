from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import credentials, initialize_app, auth
import firebase_admin
from fastapi.middleware.cors import CORSMiddleware
from service import main
from fastapi import Form

app = FastAPI()

# Initialize Firebase Admin SDK
cred = credentials.Certificate("certi.json")  # Replace with your service account key file
if not firebase_admin._apps:
    firebase_app = initialize_app(cred)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this list to include the origins you want to allow
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to extract and verify the Firebase ID token from the bearer token
security = HTTPBearer()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(token.credentials)
        return decoded_token
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token",
        ) from e
    except auth.ExpiredIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired ID token",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from e

@app.post("/get_repo_info")
async def protected_route(request_data: dict, current_user: dict = Depends(get_current_user)):
    githubUrl = request_data.get("githubUrl")
    res = main(githubUrl)
    return {"message": "You are authenticated!", "result": res}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt

import database
import auth
from ai_engine import generate_simulation_html

app = FastAPI(title="Physics AI Backend")

# Enable CORS for Flutter Web testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change to the actual domain
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Pydantic Schemas
class UserCreate(BaseModel):
    email: str
    phone_number: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    phone_number: str
    is_premium: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class SimulationRequest(BaseModel):
    question: str

# Dependency to get current user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(database.User).filter(database.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(database.User).filter((database.User.email == user.email) | (database.User.phone_number == user.phone_number)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or Phone Number already registered")
    
    hashed_pw = auth.get_password_hash(user.password)
    # Grant premium by default during development so you can test the AI simulator
    new_user = database.User(email=user.email, phone_number=user.phone_number, hashed_password=hashed_pw, is_premium=True)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(database.get_db)):
    db_user = db.query(database.User).filter(database.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = auth.create_access_token(data={"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
def read_users_me(current_user: database.User = Depends(get_current_user)):
    return current_user

# ----------------- PREMIUM AI ENDPOINT -----------------

@app.post("/api/simulate")
def generate_simulation(
    request: SimulationRequest, 
    current_user: database.User = Depends(get_current_user)
):
    # Enforce Premium Subscription
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This feature requires a Premium Subscription."
        )
    
    # User is premium, generate the simulation
    html_output = generate_simulation_html(request.question)
    
    return {"html": html_output}

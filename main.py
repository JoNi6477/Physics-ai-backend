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

# ----------------- DYNAMIC CLOUD CONTENT & UPDATE MANAGEMENT -----------------

@app.get("/api/config")
def get_app_config():
    """
    Allows the app to check for updates and global announcements dynamically.
    """
    return {
        "latest_version": "1.0.1",
        "minimum_version": "1.0.0",
        "update_url": "https://letsplaywithphysics.in/app-release.apk",
        "update_message": "A new version of Let's Play With Physics is available with enhanced simulations and features!",
        "announcement": "Welcome to Let's Play With Physics! Master JEE & NEET with interactive AI simulations."
    }

@app.get("/api/features")
def get_dashboard_features():
    """
    Returns features enabled on the dashboard.
    You can turn features ON or OFF here anytime without updating the APK!
    """
    return [
        {
            "id": "ai_sim",
            "title": "AI Simulator",
            "subtitle": "Physics Sims",
            "icon": "rocket_launch",
            "color": "0xFF44AAFF",
            "is_enabled": True
        },
        {
            "id": "formula_sheets",
            "title": "Formula Sheets",
            "subtitle": "JEE & NEET",
            "icon": "functions",
            "color": "0xFFF7C948",
            "is_enabled": True
        },
        {
            "id": "video_lectures",
            "title": "Video Lectures",
            "subtitle": "Full Classes",
            "icon": "play_circle_fill",
            "color": "0xFFF7C948",
            "is_enabled": False # Set to True whenever you upload video lectures!
        },
        {
            "id": "study_material",
            "title": "Study Material",
            "subtitle": "Chapter Notes",
            "icon": "menu_book",
            "color": "0xFF44AAFF",
            "is_enabled": False # Set to True whenever you upload notes!
        }
    ]

@app.get("/api/chapters/{exam_name}")
def get_chapters(exam_name: str):
    """
    Returns chapter lists and PDF links dynamically from the cloud.
    """
    neet_chapters = [
        {"title": "Kinematics", "pdf_url": "https://letsplaywithphysics.in/Kinematics%20formula%20sheet.pdf"},
        {"title": "Newton's Laws of Motion", "pdf_url": "https://letsplaywithphysics.in/Newton%20laws%20of%20motion%20formula%20sheet.pdf"},
        {"title": "Work, Power and Energy", "pdf_url": "https://letsplaywithphysics.in/Work%20power%20and%20energy%20formula%20sheet2.pdf"},
        {"title": "System of Particles & Rotational Motion", "pdf_url": "https://letsplaywithphysics.in/System%20of%20particles%20and%20rotational%20motion%20formula%20sheet.pdf"},
        {"title": "Gravitation", "pdf_url": "https://letsplaywithphysics.in/Gravitation%20formula%20sheet%20.pdf"},
        {"title": "Mechanical Properties of Matter", "pdf_url": "https://letsplaywithphysics.in/Mechanical%20properties%20of%20matter%20formula%20sheet.pdf"},
        {"title": "Thermodynamics & KTG", "pdf_url": "https://letsplaywithphysics.in/Thermodynamics%20and%20ktg%20formula%20sheet%20.pdf"},
        {"title": "Oscillations", "pdf_url": "https://letsplaywithphysics.in/Oscillations%20formula%20sheet.pdf"},
        {"title": "Waves", "pdf_url": "https://letsplaywithphysics.in/Waves.pdf"},
        {"title": "Electrostatics", "pdf_url": "https://letsplaywithphysics.in/Electrostatics%20formula%20sheet%20.pdf"},
        {"title": "Current Electricity", "pdf_url": "https://letsplaywithphysics.in/Current%20electricity%20formula%20sheet.pdf"},
        {"title": "Moving Charges and Magnetism", "pdf_url": "https://letsplaywithphysics.in/Moving%20charges%20and%20magnetism%20formula%20sheet%20.pdf"},
        {"title": "Magnetism and Matter", "pdf_url": "https://letsplaywithphysics.in/Magnetism%20and%20matter%20neet%20formula%20sheet.pdf"},
        {"title": "Electromagnetic Induction (EMI)", "pdf_url": "https://letsplaywithphysics.in/EMI%20formula%20sheet.pdf"},
        {"title": "Alternating Current (AC)", "pdf_url": "https://letsplaywithphysics.in/AC%20formula%20sheet.pdf"},
        {"title": "Ray Optics", "pdf_url": "https://letsplaywithphysics.in/Ray%20optics%20formula%20sheet.pdf"},
        {"title": "Wave Optics", "pdf_url": "https://letsplaywithphysics.in/Wave_optics_formula_sheet%20(1).pdf"},
        {"title": "Dual Nature of Radiation", "pdf_url": "https://letsplaywithphysics.in/Dual%20nature%20of%20the%20radiation.pdf"},
        {"title": "Modern Physics", "pdf_url": "https://letsplaywithphysics.in/Modern%20physics%20formula%20sheet%20.pdf"}
    ]

    jee_chapters = [
        {"title": "Kinematics", "pdf_url": "https://letsplaywithphysics.in/Kinematics%20formula%20sheet2.pdf"},
        {"title": "Newton's Laws of Motion", "pdf_url": "https://letsplaywithphysics.in/Newton%20laws%20of%20motion%20formula%20sheet2.pdf"},
        {"title": "Work, Power and Energy", "pdf_url": "https://letsplaywithphysics.in/Work%20power%20and%20energy%20formula%20sheet2.pdf"},
        {"title": "System of Particles & Rotational Motion", "pdf_url": "https://letsplaywithphysics.in/System%20of%20particles%20and%20rotational%20motion%20formula%20sheet.pdf"},
        {"title": "Gravitation", "pdf_url": "https://letsplaywithphysics.in/Gravitation%20formula%20sheet%20.pdf"},
        {"title": "Thermodynamics", "pdf_url": "https://letsplaywithphysics.in/Thermodynamics%20formula%20sheet2.pdf"},
        {"title": "Waves", "pdf_url": "https://letsplaywithphysics.in/Waves%20formula%20sheet%20jee.pdf"},
        {"title": "Electrostatics", "pdf_url": "https://letsplaywithphysics.in/Electrostatics%20formula%20sheet%20jee.pdf"},
        {"title": "Current Electricity", "pdf_url": "https://letsplaywithphysics.in/Current%20electricity%20formula%20sheet.pdf"},
        {"title": "Moving Charges and Magnetism", "pdf_url": "https://letsplaywithphysics.in/Moving%20charges%20and%20magnetism%20formula%20sheet%20jee.pdf"},
        {"title": "Magnetism and Matter", "pdf_url": "https://letsplaywithphysics.in/Magnetism%20and%20matter%20formula%20sheet.pdf"},
        {"title": "Dual Nature of Matter", "pdf_url": "https://letsplaywithphysics.in/Dual%20nature%20of%20matter%20formula%20sheet%20jee.pdf"}
    ]

    if "jee" in exam_name.lower():
        return jee_chapters
    return neet_chapters

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import Base, engine, get_db
# Importa os modelos necessários
from app import models
from app.models import User
# Importa schemas necessários
from app.schemas import UserCreate, UserResponse
from app.schemas import LoginRequest, LoginResponse
# Importa a função de criação de token
from datetime import timedelta
from app.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
# Importa a função para obter o usuário atual
from app.auth import get_current_user
# para conseguir o autorization automático no sweagger
from fastapi.security import OAuth2PasswordRequestForm


# Cria as tabelas automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Config para hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

#  função para verificar a senha
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Rota inicial
@app.get("/")
def root():
    return {"message": "🚀 FastAPI + PostgreSQL funcionando!"}

# Rota para obter usuário atual
# Esta rota usa a dependência get_current_user para obter o usuário autenticado
@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

# Rota para criar usuário
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Verifica se email já existe
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Cria novo usuário
    new_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Rota para listar usuários
@app.get("/users/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


# Rota de login
@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    #   Buscar usuário pelo e-mail
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    #   Gerar JWT com expiração
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    return LoginResponse(
        message="Login realizado com sucesso!",
        token=access_token
    )

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    #  Buscar usuário
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    #  Gerar JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    #  Formato padrão OAuth2
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
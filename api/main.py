from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.auth import authenticate_user, create_access_token
from api.routes import kpis
from api.database import query_df

app = FastAPI(
    title="Dashboard UTS — API Performances Académiques",
    description="API REST pour le tableau de bord décisionnel UTS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kpis.router)


@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    token = create_access_token({"sub": user["username"], "profil": user["profil"]})
    return {"access_token": token, "token_type": "bearer", "profil": user["profil"]}


@app.get("/meta/filtres")
def get_filtres():
    """Retourne les valeurs disponibles pour les filtres du dashboard."""
    filieres = query_df("SELECT code_filiere, nom_filiere FROM dim_filiere ORDER BY code_filiere")
    semestres = query_df("SELECT code_semestre FROM dim_semestre ORDER BY numero_semestre")
    annees = query_df("SELECT code_annee FROM dim_annee_academique ORDER BY annee_debut")
    return {
        "filieres": filieres.to_dict(orient="records"),
        "semestres": semestres["code_semestre"].tolist(),
        "annees": annees["code_annee"].tolist(),
        "sessions": ["Normale", "Rattrapage"],
        "genres": ["M", "F"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "message": "API Dashboard UTS opérationnelle"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

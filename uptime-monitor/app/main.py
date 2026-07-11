from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import engine, get_db, Base
from app import models
from app.checker import check_site

# Crea las tablas automáticamente si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Uptime Monitor API")

@app.get("/")
def root():
    return {"message": "Uptime Monitor API funcionando"}

@app.post("/check")
def run_check(site_name: str, url: str, db: Session = Depends(get_db)):
    result = check_site(url)

    new_check = models.Check(
        site_name=site_name,
        url=url,
        status=result["status"],
        status_code=result["status_code"],
        response_time=result["response_time"]
    )
    db.add(new_check)
    db.commit()
    db.refresh(new_check)

    return new_check

@app.get("/checks/{site_name}")
def get_history(site_name: str, db: Session = Depends(get_db)):
    checks = db.query(models.Check)\
        .filter(models.Check.site_name == site_name)\
        .order_by(models.Check.checked_at.desc())\
        .limit(50)\
        .all()
    return checks

@app.get("/sites")
def get_sites(db: Session = Depends(get_db)):
    sites = db.query(models.Check.site_name).distinct().all()
    return [s[0] for s in sites]
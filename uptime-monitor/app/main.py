from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import engine, get_db, Base, SessionLocal
from app import models
from app.checker import check_site

# Crea las tablas automáticamente si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Uptime Monitor API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lista de sitios a monitorear (por ahora fija, luego la hacemos dinámica)
SITES_TO_MONITOR = [
    {"site_name": "Google", "url": "https://www.google.com"},
    {"site_name": "GitHub", "url": "https://www.github.com"},
]

def run_scheduled_checks():
    db = SessionLocal()
    try:
        for site in SITES_TO_MONITOR:
            result = check_site(site["url"])
            new_check = models.Check(
                site_name=site["site_name"],
                url=site["url"],
                status=result["status"],
                status_code=result["status_code"],
                response_time=result["response_time"]
            )
            db.add(new_check)
        db.commit()
        print(f"Checks automáticos completados: {len(SITES_TO_MONITOR)} sitios")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(run_scheduled_checks, "interval", minutes=5)

@app.on_event("startup")
def start_scheduler():
    scheduler.start()
    run_scheduled_checks()  # corre uno inmediatamente al arrancar

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

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
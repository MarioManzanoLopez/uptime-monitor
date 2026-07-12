from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.database import engine, get_db, Base, SessionLocal
from app import models
from app.checker import check_site

# Crea las tablas automáticamente si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Uptime Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://uptime-monitor-frontend-phi.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SiteCreate(BaseModel):
    name: str
    url: str


def run_scheduled_checks():
    db = SessionLocal()
    try:
        sites = db.query(models.Site).all()
        for site in sites:
            result = check_site(site.url)
            new_check = models.Check(
                site_name=site.name,
                url=site.url,
                status=result["status"],
                status_code=result["status_code"],
                response_time=result["response_time"]
            )
            db.add(new_check)
        db.commit()
        print(f"Checks automáticos completados: {len(sites)} sitios")
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
    sites = db.query(models.Site).order_by(models.Site.created_at).all()
    return [{"name": s.name, "url": s.url} for s in sites]


@app.post("/sites")
def create_site(site: SiteCreate, db: Session = Depends(get_db)):
    new_site = models.Site(name=site.name, url=site.url)
    db.add(new_site)
    try:
        db.commit()
        db.refresh(new_site)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un sitio con ese nombre")

    # corre el primer check inmediatamente para que no se vea vacío
    result = check_site(site.url)
    new_check = models.Check(
        site_name=site.name,
        url=site.url,
        status=result["status"],
        status_code=result["status_code"],
        response_time=result["response_time"]
    )
    db.add(new_check)
    db.commit()

    return new_site


@app.delete("/sites/{site_name}")
def delete_site(site_name: str, db: Session = Depends(get_db)):
    site = db.query(models.Site).filter(models.Site.name == site_name).first()
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    db.delete(site)
    db.commit()
    return {"message": f"Sitio {site_name} eliminado"}
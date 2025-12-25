from fastapi import FastAPI, Depends, HTTPException, Form, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import select, Session as DBSession
from database import get_session, create_db_and_tables
from models import Player, Session as FSession, Payment, User
from datetime import date
import json
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import jdatetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/login", "/favicon.ico"]:
            return await call_next(request)
        
        if request.url.path.startswith("/static/"):
            return await call_next(request)
        
        if request.session.get("user_id") is None:
            return RedirectResponse(url="/login")
        
        return await call_next(request)


app.add_middleware(AuthMiddleware)

app.add_middleware(SessionMiddleware, secret_key="Avz*K5h6gyL_sd#@$5464")



create_db_and_tables()

# دیتای اولیه (برای تست: مدیر با یوزر admin و پسورد admin)
@app.on_event("startup")
def init_data():
    with next(get_session()) as session:
        if not session.exec(select(User).where(User.username == "admin")).first():
            session.add(User(username="admin", password="admin"))
            session.commit()

# چک لاگین
def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
                   
# صفحه لاگین
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: DBSession = Depends(get_session)):
    user = db.exec(select(User).where(User.username == username, User.password == password)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # درست: ذخیره user_id در session (نه cookie دستی)
    request.session["user_id"] = user.id
    
    return RedirectResponse(url="/", status_code=303)

# لگ‌اوت
@app.get("/logout")
def logout(request: Request):
    request.session.pop("user_id", None)  # پاک کردن از session
    return RedirectResponse(url="/login", status_code=303)

# صفحه اصلی (داشبورد)
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    players = db.exec(select(Player)).all()
    sessions = db.exec(select(FSession)).all()
    payments = db.exec(select(Payment)).all()

    total_debt = 0.0
    total_income = 0.0

    for player in players:
        player_debt = 0
        for s in sessions:
            try:
                player_ids = json.loads(s.players or "[]")
                if player.id in player_ids:
                    player_debt += s.price
            except:
                continue
        # کم کردن مبلغ تسویه شده
        paid = sum(p.amount for p in payments if p.player_id == player.id)
        total_income += paid  # مجموع دریافتی‌ها
        total_debt += (player_debt - paid)

    # تاریخ شمسی کامل و فارسی
    today_jalali = jdatetime.date.today()
    
    # نقشه ماه‌های شمسی
    persian_months = {
        1: "فروردین", 2: "اردیبهشت", 3: "خرداد",
        4: "تیر", 5: "مرداد", 6: "شهریور",
        7: "مهر", 8: "آبان", 9: "آذر",
        10: "دی", 11: "بهمن", 12: "اسفند"
    }
    
    persian_days = {
        2: "دوشنبه", 3: "سه‌شنبه", 4: "چهارشنبه",
        5: "پنج‌شنبه", 6: "جمعه", 0: "شنبه", 1: "یکشنبه"
    }
    
    day_name = persian_days[today_jalali.weekday()]
    month_name = persian_months[today_jalali.month]
    today_persian_full = f"{day_name} {today_jalali.day} {month_name} {today_jalali.year}"

    return templates.TemplateResponse("home.html", {
        "request": request,
        "total_income": total_income,
        "total_debt": total_debt,
        "today_persian_full": today_persian_full,
        "today_gregorian": date.today().strftime("%Y-%m-%d"),
        "players_count": len(players),
        "sessions_count": len(sessions)
    })

# مدیریت بازیکنان
@app.get("/players", response_class=HTMLResponse)
def players_page(request: Request, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    players = db.exec(select(Player)).all()
    return templates.TemplateResponse("players.html", {"request": request, "players": players})

@app.post("/players")
def add_player(name: str = Form(...), level: str = Form(...), db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    player = Player(name=name, level=level)
    db.add(player)
    db.commit()
    return RedirectResponse(url="/players", status_code=303)

@app.post("/players/{player_id}/edit")
def edit_player(player_id: int, name: str = Form(...), level: str = Form(...), db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(404)
    player.name = name
    player.level = level
    db.commit()
    return RedirectResponse(url="/players", status_code=303)

@app.post("/players/{player_id}/delete")
def delete_player(player_id: int, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(404)
    db.delete(player)
    db.commit()
    return RedirectResponse(url="/players", status_code=303)

# مدیریت سانس‌ها
# لیست سانس‌ها با گزینه ویرایش و حذف
@app.get("/sessions", response_class=HTMLResponse)
def sessions_page(request: Request, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    sessions = db.exec(select(FSession).order_by(FSession.date.desc())).all()
    
    # پیش‌پردازش: تبدیل players از string به list و استخراج نام بازیکنان
    players_dict = {p.id: p.name for p in db.exec(select(Player)).all()}  # دیکشنری برای lookup سریع
    
    processed_sessions = []
    for session in sessions:
        player_ids = json.loads(session.players or "[]")  # در صورت null، لیست خالی
        player_names = [players_dict.get(pid, "نامشخص") for pid in player_ids]
        processed_sessions.append({
            "id": session.id,
            "date": session.date,
            "price": session.price,
            "player_count": len(player_ids),
            "player_names": player_names
        })
    
    return templates.TemplateResponse("sessions.html", {
        "request": request,
        "sessions": processed_sessions
    })

# فرم ویرایش سانس
@app.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
def edit_session_form(session_id: int, request: Request, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    session = db.get(FSession, session_id)
    if not session:
        raise HTTPException(404, "سانس پیدا نشد")
    players = db.exec(select(Player)).all()
    selected_player_ids = json.loads(session.players)
    return templates.TemplateResponse("session_form.html", {
        "request": request,
        "session": session,
        "players": json.dumps([{"id": p.id, "name": p.name} for p in players]),
        "selected_players": json.dumps(selected_player_ids)
    })

@app.get("/sessions/new", response_class=HTMLResponse)
def new_session_form(request: Request, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    players = db.exec(select(Player)).all()
    return templates.TemplateResponse("session_form.html", {
        "request": request,
        "session": None,  # یعنی حالت ایجاد جدید
        "players": json.dumps([{"id": p.id, "name": p.name} for p in players]),
        "selected_players": json.dumps([])  # هیچ بازیکنی از قبل انتخاب نشده
    })

@app.post("/sessions")
def add_session(
    date_str: str = Form(...),
    price: float = Form(...),
    players_json: str = Form(...),
    db: DBSession = Depends(get_session),
    user=Depends(get_current_user)
):
    session_date = date.fromisoformat(date_str)
    try:
        player_ids = json.loads(players_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="داده بازیکنان نامعتبر است")
    
    # چک تکراری نبودن بازیکن
    if len(player_ids) != len(set(player_ids)):
        raise HTTPException(status_code=400, detail="بازیکن تکراری مجاز نیست")
    
    new_session = FSession(
        date=session_date,
        price=price,
        players=json.dumps(player_ids)
    )
    db.add(new_session)
    db.commit()
    
    return RedirectResponse(url="/sessions", status_code=303)

# ذخیره تغییرات سانس
@app.post("/sessions/{session_id}/edit")
def update_session(session_id: int, date_str: str = Form(...), price: float = Form(...), players_json: str = Form(...),
                   db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    session = db.get(FSession, session_id)
    if not session:
        raise HTTPException(404, "سانس پیدا نشد")
    
    session.date = date.fromisoformat(date_str)
    session.price = price
    player_ids = json.loads(players_json)
    if len(player_ids) != len(set(player_ids)):
        raise HTTPException(400, "بازیکن تکراری مجاز نیست")
    
    session.players = json.dumps(player_ids)
    db.commit()
    return RedirectResponse(url="/sessions", status_code=303)

# حذف سانس
@app.post("/sessions/{session_id}/delete")
def delete_session(session_id: int, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    session = db.get(FSession, session_id)
    if not session:
        raise HTTPException(404, "سانس پیدا نشد")
    db.delete(session)
    db.commit()
    return RedirectResponse(url="/sessions", status_code=303)

# گزارش بدهی‌ها
@app.get("/debts", response_class=HTMLResponse)
def debts_page(request: Request, db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    players = db.exec(select(Player)).all()
    sessions = db.exec(select(FSession)).all()
    payments = db.exec(select(Payment)).all()

    debts = {}
    for player in players:
        count = 0
        total_debt = 0.0  # float برای دقت بیشتر
        for s in sessions:
            player_ids = json.loads(s.players)  # لیست integerها
            if player.id in player_ids:  # مستقیم integer با integer چک کن
                count += 1
                total_debt += s.price
        paid = sum(p.amount for p in payments if p.player_id == player.id)
        debts[player.id] = {
            "count": count,
            "total_debt": total_debt,
            "paid": paid,
            "remaining": total_debt - paid
        }

    return templates.TemplateResponse("debts.html", {"request": request, "players": players, "debts": debts})

@app.post("/payments")
def add_payment(player_id: int = Form(...), amount: float = Form(...), db: DBSession = Depends(get_session), user=Depends(get_current_user)):
    payment = Payment(player_id=player_id, amount=amount, date=date.today())
    db.add(payment)
    db.commit()
    return RedirectResponse(url="/debts", status_code=303)

@app.get("/backup", response_class=FileResponse)
def backup_database(user=Depends(get_current_user)):
    return FileResponse("database.db", media_type="application/x-sqlite3", filename="database.db")

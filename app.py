import code

from flask import Flask, render_template, request, redirect, session
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from user_agents import parse
from urllib.parse import urlparse
from sqlalchemy import (or_, func, cast, String)
from sqlalchemy import func
import os, requests, time, random, math
import click
import subprocess
from datetime import datetime

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

app.config.from_object(Config)
db = SQLAlchemy(app)
#db.init_app(app)


migrate = Migrate(app, db)
from models import *#db, User, Link, ClickLog
limiter = Limiter(get_remote_address, app=app)

# --------------------
# GOLBAL DATA variable
# --------------------
GOLBAL_DATA_LOADED = False

dethi_tk = {}
namhoc_tk = {}
tinhthanh_tk = {}
link_tk = {}

# --------------------
# Helpers
# --------------------
def current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

def get_device(ua):
    ua = parse(ua)
    return "Mobile" if ua.is_mobile else "Desktop"

def get_country(ip):
    return "Vietnam"

def calc_money(country):
    return 0.002 if country == "Vietnam" else 0.005

def check_title(title):
    checktinhthanh = None
    checknamhoc = None
    checkde = None
    #title = title
    with open("static/data/dethi.txt",encoding='utf-8') as f: de = [l.strip() for l in f]
    for t in de:
        if t in title:
            checkde = t
            break
    if checkde in ["DHBB","Olympic 30/4"]:
        checktinhthanh = "Toàn quốc"
        for x in range(2000,2050):
            if str(x) in title.strip():
                checknamhoc = str(x)+"-"+ str(x+1)
                break
    with open("static/data/tinhthanh.txt",encoding='utf-8') as f: tinhthanh = [l.strip() for l in f]
    for t in tinhthanh:
        if t in title:
            checktinhthanh = t
            break
    for x in range(2000,2050):
        if str(x)+"-"+ str(x+1) in title.strip():
            checknamhoc = str(x)+"-"+ str(x+1)
            break
    
    return checktinhthanh, checknamhoc, checkde

def load_statistics():
    dethi_tk = {}
    namhoc_tk = {}
    tinhthanh_tk = {}
    link_tk = {}
    for l in Dethi.query.all():
        checktinhthanh, checknamhoc, checkde = check_title(l.title)
        if checkde not in dethi_tk: dethi_tk[checkde] = 0
        dethi_tk[checkde] = dethi_tk[checkde] + 1
        if checknamhoc not in namhoc_tk: namhoc_tk[checknamhoc] = 0
        namhoc_tk[checknamhoc] = namhoc_tk[checknamhoc] + 1
        if checktinhthanh not in tinhthanh_tk: tinhthanh_tk[checktinhthanh] = 0
        tinhthanh_tk[checktinhthanh] = tinhthanh_tk[checktinhthanh] + 1
    for l in Link.query.all():
        if l.loai != "all":
            link_tk[l.short_code] = [l.clicks, l.title.strip().replace("Đề thi HSG","").strip().replace("năm học","").strip()]
    return dethi_tk, namhoc_tk, tinhthanh_tk, link_tk

# Load thống kê
def thongke(fn):
    path = os.path.join(app.static_folder, "data", fn)

    ds = []

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if "|" in line:
                    ten, sl = line.split("|", 1)

                    ds.append({
                        "ten": ten,
                        "soluong": sl
                    })

    return ds
@app.route("/health")
def health():
    return "OK"
# --------------------
# Auth
# --------------------
@app.route("/register", methods=["GET","POST"])
def register():
    user = current_user()
    if user:
        return redirect("/links")
    if request.method == "POST":
        u = request.form["username"]
        p = generate_password_hash(request.form["password"])

        if User.query.filter_by(username=u).first():
            return "User đã tồn tại"

        db.session.add(User(username=u, password=p))
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    user = current_user()

    if user:
        return redirect("/links")

    error = None

    if request.method == "POST":

        # ====================================
        # CLOUDFLARE TURNSTILE VERIFY
        # ====================================

        token = request.form.get(
            "cf-turnstile-response"
        )

        verify = requests.post(

            "https://challenges.cloudflare.com/turnstile/v0/siteverify",

            data={

                "secret": app.config["TURNSTILE_SECRET_KEY"],

                "response": token,

                "remoteip": request.remote_addr

            }

        ).json()

        # DEBUG
        print("Turnstile verify:", verify)

        # ====================================
        # VERIFY FAILED
        # ====================================

        if not verify.get("success"):

            error = "Xác minh Cloudflare thất bại."

            return render_template(
                "login.html",
                error=error,
                TURNSTILE_SITE_KEY=app.config["TURNSTILE_SITE_KEY"]
            )

        # ====================================
        # LOGIN
        # ====================================

        username = request.form.get("username")

        password = request.form.get("password")

        u = User.query.filter_by(
            username=username
        ).first()

        if not u:

            error = "Tên đăng nhập không tồn tại."

        elif not check_password_hash(
            u.password,
            password
        ):

            error = "Sai mật khẩu."

        else:

            session["user_id"] = u.id
            session["username"] = u.username
            session["role"] = u.role

            return redirect("/links")

    return render_template(
        "login.html",
        error=error,
        TURNSTILE_SITE_KEY=app.config["TURNSTILE_SITE_KEY"]
    )
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --------------------
# Dashboard
# --------------------
@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user or user.role != "admin":
        return redirect("/login")

    links = Link.query.filter_by(user_id=user.id).all()

    total = db.session.query(db.func.sum(ClickLog.revenue))\
        .filter_by(user_id=user.id).scalar() or 0

    return render_template("dashboard.html", links=links, money=total)
# --------------------
# Edit link
# --------------------
@app.route("/edit_link/<code>", methods=["POST", "GET"])
def edit_link(code):
    success = None
    user = current_user()
    if not user:
        return redirect("/login")
    link = Link.query.filter_by(short_code=code, user_id=user.id).first()
    
    if request.method == "POST":
        if not link:
            link = Link.query.filter_by(short_code=request.form["code"], user_id=user.id).first()
        if not link: success = "Link không tồn tại"
        else:
            url = request.form["url"]
            title = request.form["title"]
            link.original_url = url
            link.title = title
            db.session.commit()
            success = "Cập nhật thành công"
    return render_template("edit_link.html", link=link, success=success)

# --------------------
# Delete link
# --------------------
@app.route("/delete_link/<code>", methods=["POST", "GET"])
def delete_link(code):
    user = current_user()
    if not user:
        return redirect("/login")

    link = Link.query.filter_by(short_code=code, user_id=user.id).first()
    if not link:
        return "Link not found"

    db.session.delete(link)
    db.session.commit()

    return redirect("/links")

# --------------------
# Edit Đề thi
# --------------------
@app.route("/edit_dethi/<int:idd>", methods=["POST", "GET"])
def edit_dethi(idd=None):
    user = current_user()
    if not user:
        return redirect("/login")
    dethi = Dethi.query.filter_by(id=idd).first()
    if request.method == "POST":
        dethi = Dethi.query.filter_by(id=request.form["id"]).first()
        if not dethi: return "Đề thi không tồn tại"
        url = request.form["url"]
        title = request.form["title"]
        debai = request.form["debai"]
        debai_id = request.form["debai_id"]
        
        l = Link.query.filter_by(original_url=debai).first()
        huongdan = request.form["huongdan"]
        huongdan_id = request.form["huongdan_id"]

        test_label = [request.form["test"+str(i)+"_label"] for i in range(1, 6)]
        test = [request.form["test"+str(i)] for i in range(1, 6)]
        test_id = [request.form["test"+str(i)+"_id"] for i in range(1, 6)]

        dethi.title = title
        l = Link.query.filter_by(dethi_id=dethi.id,loai="all").first()
        if l is None:
            l = Link(user_id=user.id, original_url=url, title=title, loai="all")
            db.session.add(l)
            #db.session.commit()
            dethi.link = l.id
            db.session.commit()
        else:
            l.original_url = url
            l.title = title

        l = Link.query.filter(Link.id == debai_id).first() if debai_id != -1 else None
        if debai.strip()!="":
            if l is None:
                tmp_title = "<b>[Đề bài]</b> - "+dethi.title.replace("Đề thi HSG","").strip().replace("năm học","").strip()
                l = Link(user_id=user.id, original_url=debai, title=tmp_title, loai="Đề")
                db.session.add(l)
                #db.session.commit()
                l.dethi_id = dethi.id
                db.session.commit()
            else:
                l.original_url = debai
                l.title = "<b>[Đề bài]</b> - "+dethi.title.replace("Đề thi HSG","").strip().replace("năm học","").strip()
    
        l = Link.query.filter(Link.id == huongdan_id).first() if huongdan_id != -1 else None
        if huongdan.strip()!="":
            if l is None:
                tmp_title = "<b>[Hướng dẫn]</b> - "+dethi.title.replace("Đề thi HSG","").strip().replace("năm học","").strip()
                l = Link(user_id=user.id, original_url=huongdan, title=tmp_title, loai="Hướng dẫn")
                db.session.add(l)
                #db.session.commit()
                l.dethi_id = dethi.id
                db.session.commit()
            else:
                l.original_url = huongdan
                l.title = "<b>[Hướng dẫn]</b> - "+dethi.title.replace("Đề thi HSG","").strip().replace("năm học","").strip()

        for i in range(1,6):
            if test[i-1].strip()=="" or test_label[i-1].strip()=="" or test_id[i-1]==-1: continue
            tmp_title = "<b>[" + test_label[i-1] + "]</b> - " + dethi.title.replace('Đề thi HSG', '').strip().replace('năm học', '').strip()
            l = Link.query.filter(Link.id == test_id[i-1]).first()
            if l is None:
                l = Link(user_id=user.id, original_url=test[i-1], title=tmp_title, loai="Test")
                db.session.add(l)
                #db.session.commit()
                l.dethi_id = dethi.id
                db.session.commit()
            else:
                l.original_url = test[i-1]
                l.title = tmp_title
        db.session.commit()

    tmp={"id": dethi.id,"title": dethi.title, "original_url": "", "debai": "", "huongdan": "","debai_id": -1, "huongdan_id": -1}
    for i in range(1,6):
        tmp["test"+str(i)] = ""
        tmp["test"+str(i)+"_label"] = ""
        tmp["test"+str(i)+"_id"] = -1
    
    i=0
    for l in dethi.links:
        if l.loai=="all":
            tmp["original_url"] = l.original_url
        if l.loai == "Đề":
            tmp["debai"] = l.original_url
            tmp["debai_id"] = l.id
        if l.loai == "Hướng dẫn":
            tmp["huongdan"] = l.original_url
            tmp["huongdan_id"] = l.id
        if l.loai == "Test":
            i+=1
            tmp["test"+str(i)] = l.original_url
            tmp["test"+str(i)+"_label"] = l.title.split("]</b>")[0].replace("<b>[","").strip()
            tmp["test"+str(i)+"_id"] = l.id
    return render_template("edit_dethi.html", dethi=tmp)

# --------------------
# Delete Đề thi
# --------------------
@app.route("/delete_dethi/<int:idd>", methods=["POST", "GET"])
def delete_dethi(idd):
    user = current_user()
    if not user:
        return redirect("/login")

    dethi = Dethi.query.filter_by(id=idd).first()
    if not dethi:
        return "Link not found"
    link = Link.query.filter_by(dethi_id=dethi.id).first()
    if link:
        db.session.delete(link)
    db.session.delete(dethi)
    db.session.commit()

    return redirect("/createdethi")


# --------------------
# Create Đề thi
# --------------------
@app.route("/createdethi", methods=["GET","POST"])
def createdethi():
    success = None
    user = current_user()
    if not user or user.role != "admin":
        return redirect("/login")
    
    if request.method == "POST":
        title = request.form["title"]
        url = request.form["url"]
        link = Link.query.filter_by(original_url=url).first()
        d = Dethi.query.filter_by(title=title).first()
        checktinhthanh, checknamhoc, checkde = check_title(title)
        if checktinhthanh is None:
            success = "Tên tỉnh/thành phố không hợp lệ. Vui lòng kiểm tra lại."
        elif checknamhoc is None:
            success = "Năm học không hợp lệ. Vui lòng kiểm tra lại."
        elif checkde is None:
            success = "Tên đề thi không hợp lệ. Vui lòng kiểm tra lại."
        elif d:
            success = "Tên đề thi đã tồn tại."
        elif link:
            success = "Đường dẫn đã tồn tại. Vui lòng sử dụng đường dẫn khác."
        else:
            dethi = Dethi(title=title)
            link = Link(user_id=user.id, original_url=url, title=title, loai="all")
            dethi.links.append(link)
            db.session.add(dethi)
            db.session.commit()
            success = "Tạo Đề thi thành công"
            #Cập nhật thống kê
            global dethi_tk, namhoc_tk, tinhthanh_tk
            if checktinhthanh not in tinhthanh_tk: tinhthanh_tk[checktinhthanh] = 0
            tinhthanh_tk[checktinhthanh] = tinhthanh_tk[checktinhthanh] + 1
            if checknamhoc not in namhoc_tk: namhoc_tk[checknamhoc] = 0
            namhoc_tk[checknamhoc] = namhoc_tk[checknamhoc] + 1
            if checkde not in dethi_tk: dethi_tk[checkde] = 0
            dethi_tk[checkde] = dethi_tk[checkde] + 1 
    return render_template("createdethi.html", success=success)

# --------------------
# Create Link
# --------------------
@app.route("/createlink", methods=["GET","POST"])
def createlink():
    success = None
    user = current_user()
    if not user or user.role != "admin":
        return redirect("/login")
    page = request.args.get("page",1,type=int)

    if request.method == "POST":
        url = request.form["url"]
        title = request.form["title"]
        l = Link.query.filter_by(original_url=url).first()        
        if l:
            success = "Link đã tồn tại."
        else:
            link = Link(user_id=user.id, original_url=url, title=title, loai="Khác")
            db.session.add(link)
            db.session.commit()
            success = "Tạo link thành công"
            
    query = Link.query
    pagination = query.order_by(Link.created_at.desc()).paginate(page=page,per_page=50,error_out=False)

    # =========================
    # FORMAT DATA
    # =========================

    links = []

    for l in pagination.items:

        tmp = {
            "id": l.id,
            "title": l.title.strip(),
            "short_code": l.short_code,
            "clicks": l.clicks,
            "created_at": l.created_at,
            "url": request.host_url + l.short_code,
            "original_url": l.original_url if user and user.role == "admin" else None
        }
        # dethi = Dethi.query.filter_by(link=l.id).first()
        # if dethi and l.loai in ["Đề", "Hướng dẫn", "Test"]:

        #     tmp["title"] =l.title.strip() + " - " + dethi.title.replace("Đề thi HSG","").strip().replace("năm học","").strip()
        links.append(tmp)
    total_clicks = db.session.query(func.sum(Link.clicks)).scalar() or 0
    return render_template("createlink.html",links=links, success=success,pagination=pagination,total_clicks=total_clicks)

# --------------------
# CAPTCHA Turnstile
# --------------------
@app.route("/<code>", methods=["GET","POST"])
@limiter.limit("10/minute")
def captcha(code):
    link = Link.query.filter_by(short_code=code).first()
    if not link:
        return "Not found"

    ua = request.headers.get("User-Agent","").lower()
    if "bot" in ua:
        return "Bot blocked"

    if request.method == "POST":
        token = request.form.get("cf-turnstile-response")
        

        verify = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": app.config["TURNSTILE_SECRET_KEY"],
                "response": token,
                "remoteip": request.remote_addr
            }
        ).json()

        if verify.get("success"):
            session["ok_"+code] = time.time()
            return redirect("/ads/"+code)

        return "Xác minh thất bại"
    total_clicks = db.session.query(func.sum(Link.clicks)).scalar() or 0

    return render_template("captcha.html", site_key=app.config["TURNSTILE_SITE_KEY"],title=link.title,total_clicks=total_clicks)

# --------------------
# ADS
# --------------------
@app.route("/ads/<code>")
def ads(code):
    
    ts = session.get("ok_"+code)

    if not ts or time.time() - ts > 120:
        return redirect("/"+code)

    link = Link.query.filter_by(short_code=code).first()
    delay = math.sqrt(link.clicks) if link.clicks < 1000 else math.log2(link.clicks) + math.sqrt(link.clicks)
    delay = max(math.floor(delay), 10)
    user = current_user()
    if user is None : delay *=2
    #Tổng số clicks
    total_clicks = db.session.query(func.sum(Link.clicks)).scalar() or 0
    return render_template("ads.html", delay=delay, code=code,title=link.title,total_clicks=total_clicks)

@app.route("/pushoj/<code>", methods=["GET","POST"])
def pushoj(code=None):
    success = None
    dethi = None
    tmpdethi = {"title": "", "oj": "","code": code}
    link = Link.query.filter_by(short_code=code).first()
    if link: dethi = link.dethi_obj
    if request.method == "POST":
        code = request.form["code"]
        link = Link.query.filter_by(short_code=code).first()
        if link and link.dethi_obj:
            dethi = link.dethi_obj
            oj = request.form["oj"]
            domain = urlparse(oj).netloc 
            if domain not in app.config["ALLOWED_OJ"]:
                success = "OJ không hợp lệ. Các OJ được hỗ trợ: " + ", ".join(app.config["ALLOWED_OJ"])
            else:
                dethi.oj = oj
                db.session.commit()
                success = "Cập nhật OJ thành công"
    if dethi is None:
        success = "Đề thi không tồn tại"
    else:
        tmpdethi = {"title": dethi.title, "oj": dethi.oj,"code": code}
    return render_template("pushoj.html", dethi=tmpdethi, success=success)

# --------------------
# Redirect
# --------------------
@app.route("/go/<code>")
def go(code):
    ts = session.get("ok_"+code)
    if not ts:
        return redirect("/"+code)

    link = Link.query.filter_by(short_code=code).first()
    if not link:
        return "Not found"

    session.pop("ok_"+code, None)

    country = get_country(request.remote_addr)
    device = get_device(request.headers.get("User-Agent"))

    money = calc_money(country)

    db.session.add(ClickLog(
        link_id=link.id,
        user_id=link.user_id,
        country=country,
        device=device,
        revenue=money
    ))

    link.clicks += 1
    db.session.commit()
    if link.short_code not in link_tk:
        link_tk[link.short_code] = [0, link.title]
    link_tk[link.short_code][0] = link.clicks

    

    return redirect(link.original_url)

# --------------------
# Danh sách Đề thi
# --------------------
@app.route("/dethi")
def dethi():
    user = current_user()
    page = request.args.get("page",1,type=int)

    # =========================
    # FILTER
    # =========================

    loaide = request.args.get("loai_de")
    tinhthanh = request.args.get("tinh_thanh")
    namhoc = request.args.get("nam_hoc")

    # =========================
    # QUERY
    # =========================

    query = Dethi.query

    # =========================
    # FILTER SQL
    # =========================

    if loaide: query = query.filter(Dethi.title.ilike(f"%{loaide}%"))
    if tinhthanh: query = query.filter(Dethi.title.ilike(f"%{tinhthanh}%"))
    if namhoc: query = query.filter(Dethi.title.ilike(f"%{namhoc}%"))

    # =========================
    # ORDER + PAGINATION
    # =========================

    pagination = query.order_by(Dethi.created_at.desc()).paginate(page=page,per_page=50,error_out=False)

    # =========================
    # FORMAT DATA
    # =========================

    links = []

    for l in pagination.items:

        tmp = {
            "id": l.id,
            "title": l.title.replace("Đề thi HSG","").strip().replace("năm học","").strip(),
            "oj" : l.oj if l.oj else None
        }
        link = Link.query.filter_by(dethi_id=l.id).all()
        i=0
        for l in link:
            if tmp["oj"] is None: tmp["oj"] = l.short_code
            if l.loai=="all":
                tmp["original_url"] = l.original_url if user and user.role == "admin" else None
            if l.loai == "Đề":
                tmp["debai"] = l.short_code
            if l.loai == "Hướng dẫn":
                tmp["huongdan"] = l.short_code
            if l.loai == "Test":
                i+=1
                tmp["test"+str(i)] = l.short_code
                tmp["test"+str(i)+"_label"] = l.title.split("]</b>")[0].replace("<b>[","").strip()

        links.append(tmp)

    # =========================
    # RENDER
    # =========================

    return render_template(
        "dethi.html",
        links=links,
        pagination=pagination,
        loaide=loaide,
        tinhthanh=tinhthanh,
        namhoc=namhoc
    )

@app.route("/go_dethi/<idd>")
def go_dethi(idd):
    dethi = Dethi.query.filter_by(id=idd).first()
    if not dethi:
        return "Not found"
    link = Link.query.filter_by(dethi_id=dethi.id).all()
    tmp = dethi.title
    tmp+="<br>==========================="
    for l in link:
 
        if l.loai == "Đề":
            tmp += "<br>Đề bài: <a href='/go/" + l.short_code + "'>" + request.host_url + l.short_code + "</a>"
        if l.loai == "Hướng dẫn":
            tmp += "<br>Hướng dẫn: <a href='/go/" + l.short_code + "'>" + request.host_url + l.short_code + "</a>"
        if l.loai == "Test":
            label = l.title.split("]</b>")[0].replace("<b>[","").strip()
            tmp += f"<br>Test {label}: <a href='/go/{l.short_code}'>{request.host_url}{l.short_code}</a>"
            
    return tmp


@app.route("/links")
def links():

    user = current_user()
    page = request.args.get("page",1,type=int)

    keyword = request.args.get("q","",type=str).strip()

    # =========================
    # BASE QUERY
    # =========================

    query = Link.query.filter(Link.loai != "all")
    #query = Link.query

    # =========================
    # SEARCH
    # =========================

    if keyword:
        keyword2 = keyword.lower()

        query = (

            query

            .filter(

                or_(

                    func.unaccent(
                        func.lower(Link.title)
                    ).ilike(

                        f"%{keyword2}%"
                    ),

                    func.similarity(

                        func.unaccent(
                            func.lower(Link.title)
                        ),

                        func.unaccent(keyword2)

                    ) > 0.1

                )

            )

            .order_by(

                func.similarity(

                    func.unaccent(
                        func.lower(Link.title)
                    ),

                    func.unaccent(keyword2)

                ).desc(),

                Link.created_at.desc()

            )

        )
    else:
        query = query.order_by(Link.created_at.desc())

    # =========================
    # PAGINATION
    # =========================

    pagination = query.paginate(page=page,per_page=50,error_out=False)

    # =========================
    # FORMAT DATA
    # =========================

    links = []

    for l in pagination.items:

        title = (
            l.title
            .replace("Đề thi HSG", "")
            .replace("năm học", "")
            .strip()
        )

        tmp = {

            "id": l.id,
            "title": title.replace("Đề thi HSG", "").replace("năm học", "").strip(),
            "short_code": l.short_code,
            "clicks": l.clicks,
            "created_at": l.created_at,
            "url": request.host_url + l.short_code,
            "original_url": (
                l.original_url
                if user and user.role == "admin"
                else None
            )
        }


        links.append(tmp)
    #Tổng số clicks
    total_clicks = db.session.query(func.sum(Link.clicks)).scalar() or 0
    # =========================
    # RENDER
    # =========================

    return render_template(
        "links.html",
        links=links,
        pagination=pagination,
        keyword=keyword,
        total_clicks=total_clicks
    )
def ensure_loaded():

    global GOLBAL_DATA_LOADED
    global dethi_tk, namhoc_tk, tinhthanh_tk, link_tk
    if not GOLBAL_DATA_LOADED:
        dethi_tk, namhoc_tk, tinhthanh_tk, link_tk = load_statistics()
        GOLBAL_DATA_LOADED = True
@app.context_processor
def inject_global():

    ensure_loaded()

    return dict(
        dethi_tk=dict(sorted(dethi_tk.items(), key=lambda x: x[1], reverse=True)),
        namhoc_tk=dict(sorted(namhoc_tk.items(), key=lambda x: x[0],reverse=True)),
        tinhthanh_tk=dict(sorted(tinhthanh_tk.items(), key=lambda x: x[0], reverse=False)),
        link_tk=dict(sorted(link_tk.items(), key=lambda x: x[1][0], reverse=True))
    )
@app.route("/")
def home():
    return redirect("/links")
@app.route("/hp")
def hp():
    # for de in Dethi.query.all():
    #     db.session.delete(de)
    # db.session.commit()
    # for link in Link.query.all():
    #     de = Dethi(title=link.title,created_at=link.created_at)
    #     de.links.append(link)
    #     db.session.add(de)
    # db.session.commit()
    
    return "Hello, HP!"

@app.cli.command("backup")
def backup_db():

    backup_dir = "backups"

    os.makedirs(backup_dir, exist_ok=True)

    filename = datetime.now().strftime(
        "backup_%Y_%m_%d_%H_%M_%S.backup"
    )

    filepath = os.path.join(
        backup_dir,
        filename
    )

    db_url = app.config["SQLALCHEMY_DATABASE_URI"]

    subprocess.run([
        r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        "-F", "c",          # custom format
        "-v",               # verbose
        "--no-owner",
        "--no-privileges",
        db_url,
        "-f",
        filepath
        ],check=True)

    print(f"Backup created: {filepath}")
# --------------------
# RUN
# --------------------
if __name__ == "__main__":
    app.run(debug=True)
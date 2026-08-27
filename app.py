from flask import Flask , render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = "mysecretkey"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    bookings = db.relationship("Booking", backref="user")


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    blacklisted = db.Column(db.Boolean, default=False)
    schedules = db.relationship("TrekSchedule", backref="staff")

class Trek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trek_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)     
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    schedules = db.relationship("TrekSchedule", backref="trek")


class TrekSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trek_id = db.Column(db.Integer,db.ForeignKey("trek.id"),nullable=False)
    staff_id = db.Column(db.Integer,db.ForeignKey("staff.id"),nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Open")
    bookings = db.relationship("Booking", backref="schedule")

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    schedule_id = db.Column(db.Integer,db.ForeignKey("trek_schedule.id"),nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    number_of_people = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20),nullable=False,default="Confirmed")
    refund_status = db.Column(db.String(20),default="Not Applicable")


with app.app_context():
    db.create_all()
    admin = Admin.query.filter_by(email="admin@gmail.com").first()
    if not admin:
        admin = Admin(
            name="Admin",
            email="admin@gmail.com",
            password="admin123"
        )
        db.session.add(admin)
        db.session.commit()

@app.route("/")
def home():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if not user:
            session.pop("user_id", None)
            return redirect("/login")
    treks = Trek.query.all()
    return render_template("home.html",user=user,treks=treks)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session["user_id"] = user.id
            return redirect("/")
        return render_template("login.html",error="Invalid Email or Password")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email already registered."
        new_user = User(
            name=name,
            email=email,
            password=password
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.password == password:
            session.clear()
            session["admin_id"] = admin.id
            return redirect("/admin_dashboard")
        return render_template("admin_login.html",error="Invalid Email or Password")
    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin_login")
    admin = Admin.query.get(session["admin_id"])
    total_treks = Trek.query.count()
    total_users = User.query.count()
    total_staff = Staff.query.count()
    approved_staff = Staff.query.filter_by(approved=True).count()
    open_departures = TrekSchedule.query.filter_by(status="Open").count()
    closed_departures = TrekSchedule.query.filter_by(status="Closed").count()
    total_bookings = Booking.query.count()
    return render_template("admin_dashboard.html",admin=admin,total_treks=total_treks,total_users=total_users,total_staff=total_staff,approved_staff=approved_staff,open_departures=open_departures,closed_departures=closed_departures,total_bookings=total_bookings)


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")
    user = User.query.get(session["user_id"])
    if not user:
        session.pop("user_id", None)
        return redirect("/login")
    return render_template("profile.html",user=user)

@app.route("/add_trek", methods=["GET", "POST"])
def add_trek():
    if "admin_id" not in session:
        return redirect("/admin_login")
    if request.method == "POST":
        trek_name = request.form["trek_name"]
        location = request.form["location"]
        difficulty = request.form["difficulty"]
        duration = request.form["duration"]
        price = request.form["price"]
        description = request.form["description"]
        new_trek = Trek(
            trek_name=trek_name,
            location=location,
            difficulty=difficulty,
            duration=duration,
            price=price,
            description=description
        )
        db.session.add(new_trek)
        db.session.commit()
        return redirect("/admin_dashboard")
    return render_template("add_trek.html")


@app.route("/add_staff", methods=["GET", "POST"])
def add_staff():
    if "admin_id" not in session:
        return redirect("/admin_login")
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        existing_staff = Staff.query.filter_by(email=email).first()
        if existing_staff:
            return "Staff already exists."
        new_staff = Staff(
            name=name,
            email=email,
            phone=phone,
            password=password
        )
        db.session.add(new_staff)
        db.session.commit()
        return redirect("/admin_dashboard")
    return render_template("add_staff.html")


@app.route("/view_users")
def view_users():
    if "admin_id" not in session:
        return redirect("/admin_login")
    search = request.args.get("search")
    if search:
        users = User.query.filter(User.name.ilike(f"%{search}%")).all()
    else:
        users = User.query.all()
    return render_template("view_users.html",users=users)


@app.route("/staff")
def staff_list():
    if "admin_id" not in session:
        return redirect("/admin_login")
    search = request.args.get("search")
    if search:
        staff_members = Staff.query.filter(Staff.name.ilike(f"%{search}%")).all()
    else:
        staff_members = Staff.query.all()
    return render_template("staff.html",staff_members=staff_members)


@app.route("/staff_login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        staff = Staff.query.filter_by(email=email,password=password).first()
        if staff:
            session.clear()
            session["staff_id"] = staff.id
            return redirect("/staff_dashboard")
        return render_template("staff_login.html",error="Invalid Email or Password")
    return render_template("staff_login.html")


@app.route("/staff_dashboard")
def staff_dashboard():
    if "staff_id" not in session:
        return redirect("/staff_login")
    staff = Staff.query.get(session["staff_id"])
    departures = TrekSchedule.query.filter_by(staff_id=staff.id).all()
    return render_template("staff_dashboard.html",staff=staff,departures=departures)


@app.route("/view_participants/<int:schedule_id>")
def view_participants(schedule_id):
    if "staff_id" not in session:
        return redirect("/staff_login")
    schedule = TrekSchedule.query.get_or_404(schedule_id)
    if schedule.staff_id != session["staff_id"]:
        return redirect("/staff_dashboard")
    bookings = Booking.query.filter_by(schedule_id=schedule.id,status="Confirmed").all()
    return render_template("view_participants.html",schedule=schedule,bookings=bookings)


@app.route("/close_departure/<int:id>")
def close_departure(id):
    if "staff_id" not in session:
        return redirect("/staff_login")
    departure = TrekSchedule.query.get_or_404(id)
    if departure.staff_id != session["staff_id"]:
        return redirect("/staff_dashboard")
    departure.status = "Closed"
    db.session.commit()
    return redirect("/staff_dashboard")


@app.route("/open_departure/<int:id>")
def open_departure(id):
    if "staff_id" not in session:
        return redirect("/staff_login")
    departure = TrekSchedule.query.get_or_404(id)
    if departure.staff_id != session["staff_id"]:
        return redirect("/staff_dashboard")
    departure.status = "Open"
    db.session.commit()
    return redirect("/staff_dashboard")


@app.route("/approve_staff/<int:id>")
def approve_staff(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    staff = Staff.query.get_or_404(id)
    staff.approved = True
    db.session.commit()
    return redirect("/staff")


@app.route("/unapprove_staff/<int:id>")
def unapprove_staff(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    staff = Staff.query.get_or_404(id)
    staff.approved = False
    db.session.commit()
    return redirect("/staff")


@app.route("/blacklist_staff/<int:id>")
def blacklist_staff(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    staff = Staff.query.get_or_404(id)
    staff.blacklisted = True
    staff.approved = False
    db.session.commit()
    return redirect("/staff")


@app.route("/remove_blacklist/<int:id>")
def remove_blacklist(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    staff = Staff.query.get_or_404(id)
    staff.blacklisted = False
    db.session.commit()
    return redirect("/staff")


@app.route("/assign_staff/<int:id>")
def assign_staff(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    trek = Trek.query.get_or_404(id)
    available_staff = Staff.query.filter_by(approved=True,blacklisted=False).all()
    return render_template("assign_staff.html",trek=trek,available_staff=available_staff)


@app.route("/view_departures/<int:id>")
def view_departures(id):
    trek = Trek.query.get_or_404(id)
    departures = TrekSchedule.query.filter_by(trek_id=trek.id,status="Open").all()
    return render_template("view_departures.html",trek=trek,departures=departures )


@app.route("/book_trek/<int:schedule_id>", methods=["GET", "POST"])
def book_trek(schedule_id):
    if "user_id" not in session:
        return redirect("/login")
    schedule = TrekSchedule.query.get_or_404(schedule_id)
    if schedule.status == "Closed":
        return "This departure is closed for booking."
    trek = schedule.trek
    if request.method == "POST":
        number_of_people = int(request.form["number_of_people"])
        if number_of_people > schedule.available_slots:
            return "Not enough slots available."
        new_booking = Booking(
            user_id=session["user_id"],
            schedule_id=schedule.id,
            booking_date=date.today(),
            number_of_people=number_of_people
        )
        db.session.add(new_booking)
        schedule.available_slots -= number_of_people
        db.session.commit()
        return redirect("/my_bookings")
    return render_template("book_trek.html",trek=trek,schedule=schedule)


@app.route("/treks")
def view_treks():
    search = request.args.get("search")
    difficulty = request.args.get("difficulty")
    location = request.args.get("location")
    treks = Trek.query
    if search:
        treks = treks.filter(Trek.trek_name.ilike(f"%{search}%"))
    if difficulty:
        treks = treks.filter_by(difficulty=difficulty)
    if location:
        treks = treks.filter( Trek.location.ilike(f"%{location}%"))
    treks = treks.all()
    return render_template("treks.html",treks=treks)


@app.route("/manage_departures/<int:id>")
def manage_departures(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    trek = Trek.query.get_or_404(id)
    departures = TrekSchedule.query.filter_by(trek_id=trek.id).all()
    return render_template("manage_departures.html",trek=trek,departures=departures)


@app.route("/add_departure/<int:id>", methods=["GET", "POST"])
def add_departure(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    trek = Trek.query.get_or_404(id)
    if request.method == "GET":
        return render_template("add_departure.html",trek=trek,step=1)
    if request.form["action"] == "continue":
        start_date = datetime.strptime(request.form["start_date"],"%Y-%m-%d").date()
        available_slots = int(request.form["available_slots"])
        end_date = start_date + timedelta(days=trek.duration - 1)
        available_staff = []
        all_staff = Staff.query.filter_by(approved=True, blacklisted=False).all()
        for staff in all_staff:
            conflict = TrekSchedule.query.filter(TrekSchedule.staff_id == staff.id,TrekSchedule.start_date <= end_date,TrekSchedule.end_date >= start_date).first()
            if not conflict:
                available_staff.append(staff)
        return render_template("add_departure.html",trek=trek,step=2,start_date=start_date,end_date=end_date,available_slots=available_slots,available_staff=available_staff)
    start_date = datetime.strptime(request.form["start_date"],"%Y-%m-%d").date()
    end_date = datetime.strptime(request.form["end_date"],"%Y-%m-%d").date()
    available_slots = int(request.form["available_slots"])
    staff_id = int(request.form["staff_id"])
    new_departure = TrekSchedule(
        trek_id=trek.id,
        staff_id=staff_id,
        start_date=start_date,
        end_date=end_date,
        available_slots=available_slots
    )
    db.session.add(new_departure)
    db.session.commit()
    return redirect(f"/manage_departures/{trek.id}")


@app.route("/edit_trek/<int:id>", methods=["GET", "POST"])
def edit_trek(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    trek = Trek.query.get_or_404(id)
    if request.method == "POST":
        trek.trek_name = request.form["trek_name"]
        trek.location = request.form["location"]
        trek.difficulty = request.form["difficulty"]
        trek.duration = request.form["duration"]
        trek.price = int(request.form["price"])
        db.session.commit()
        return redirect("/treks")
    return render_template("edit_trek.html", trek=trek)


@app.route("/delete_trek/<int:id>")
def delete_trek(id):
    if "admin_id" not in session:
        return redirect("/admin_login")
    trek = Trek.query.get_or_404(id)
    schedules = TrekSchedule.query.filter_by(trek_id=trek.id).all()
    for schedule in schedules:
        bookings = Booking.query.filter_by(schedule_id=schedule.id).count()
        if bookings > 0:
            return redirect("/treks?delete_error=This trek cannot be deleted because it has existing bookings.")
    for schedule in schedules:
        db.session.delete(schedule)
    db.session.delete(trek)
    db.session.commit()
    return redirect("/treks")


@app.route("/my_bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect("/login")
    bookings = Booking.query.filter_by(user_id=session["user_id"]).all()
    return render_template("my_bookings.html",bookings=bookings)


@app.route("/cancel_booking/<int:id>")
def cancel_booking(id):
    if "user_id" not in session:
        return redirect("/login")
    booking = Booking.query.get_or_404(id)
    if booking.user_id != session["user_id"]:
        return redirect("/")
    if booking.status == "Cancelled":
        return redirect("/my_bookings")
    booking.status = "Cancelled"
    booking.schedule.available_slots += booking.number_of_people
    db.session.commit()
    return redirect("/my_bookings")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
    
if __name__ == "__main__":
    app.run(debug=True)
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SECRET_KEY"] = "hoppa-local-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hoppa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    accompanied = db.Column(db.Boolean, default=False)
    at_table = db.Column(db.Boolean, default=False)
    has_loyalty_card = db.Column(db.Boolean, default=False)
    loyalty_card_id = db.Column(db.Integer, db.ForeignKey("loyalty_card.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LoyaltyCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(30), unique=True, nullable=False)
    child_name = db.Column(db.String(120), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    photo_consent = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(40), nullable=True)
    card_group_key = db.Column(db.String(40), nullable=True)
    card_order_in_group = db.Column(db.Integer, nullable=True)
    birthday_free_used_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_name = db.Column(db.String(120), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    is_sibling = db.Column(db.Boolean, default=False)
    sibling_of = db.Column(db.String(120), nullable=True)
    total_minutes = db.Column(db.Integer, nullable=False)
    used_minutes = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    birthday_free_used_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, nullable=False)
    parent_visit_id = db.Column(db.Integer, db.ForeignKey("visit.id"), nullable=True)
    child_name = db.Column(db.String(120), nullable=False)
    phone_or_status = db.Column(db.String(120), nullable=False)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    checkout_time = db.Column(db.DateTime, nullable=True)
    paused = db.Column(db.Boolean, default=False)
    pause_started_at = db.Column(db.DateTime, nullable=True)
    paused_minutes = db.Column(db.Integer, default=0)
    not_stayed = db.Column(db.Boolean, default=False)
    socks_count = db.Column(db.Integer, default=0)
    balloons_swords = db.Column(db.Integer, default=0)
    balloons_flowers = db.Column(db.Integer, default=0)
    amount_paid = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), nullable=True)
    paid_cash = db.Column(db.Float, default=0.0)
    paid_card = db.Column(db.Float, default=0.0)
    used_loyalty_free = db.Column(db.Boolean, default=False)
    loyalty_card_id = db.Column(db.Integer, db.ForeignKey("loyalty_card.id"), nullable=True)
    used_birthday_free = db.Column(db.Boolean, default=False)
    loyalty_minutes_granted = db.Column(db.Integer, nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"), nullable=True)
    subscription_minutes_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PauseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visit.id"), nullable=False)
    pause_out = db.Column(db.DateTime, nullable=False)
    pause_in = db.Column(db.DateTime, nullable=True)


class LoyaltyEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loyalty_card_id = db.Column(db.Integer, db.ForeignKey("loyalty_card.id"), nullable=False)
    visit_id = db.Column(db.Integer, db.ForeignKey("visit.id"), nullable=False)
    visit_date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExtraPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SubscriptionPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    paid_cash = db.Column(db.Float, default=0.0)
    paid_card = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def minutes_between(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def format_duration(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60}m"


def is_birthday_window(bday: date, on_date: date) -> bool:
    bd_this = date(on_date.year, bday.month, bday.day)
    return abs((on_date - bd_this).days) <= 1


def compute_loyalty_reward(card_id: int) -> Optional[int]:
    entries = (
        LoyaltyEntry.query.filter_by(loyalty_card_id=card_id)
        .order_by(LoyaltyEntry.visit_date.desc())
        .limit(10)
        .all()
    )
    if len(entries) < 10:
        return None
    avg = sum(e.duration_minutes for e in entries) / 10
    if 30 <= avg <= 45:
        return 30
    if 50 <= avg <= 85:
        return 60
    if avg >= 90:
        return 9999
    return None


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def next_group_id() -> int:
    max_id = db.session.query(func.max(Visit.group_id)).scalar()
    return (max_id or 0) + 1


def current_day_range():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)
    return start, end


def extract_sibling_prefills(form_data: dict):
    items = []
    for i in range(1, 6):
        prefix = f"sibling{i}"
        name = (form_data.get(f"{prefix}_name") or "").strip()
        wants_card = bool(form_data.get(f"{prefix}_wants_card"))
        birth_date = form_data.get(f"{prefix}_birth_date") or ""
        photo_consent = form_data.get(f"{prefix}_photo_consent") or "yes"
        if name or wants_card or birth_date:
            items.append({
                "name": name,
                "wants_card": wants_card,
                "birth_date": birth_date,
                "photo_consent": photo_consent,
            })
    return items


@app.route("/")
def index():
    cards = LoyaltyCard.query.order_by(LoyaltyCard.child_name).all()
    return render_template("checkin.html", cards=cards, old_form={}, sibling_prefills=[])


@app.post("/api/loyalty/find")
def find_loyalty():
    name = request.json.get("name", "")
    card = LoyaltyCard.query.filter(LoyaltyCard.child_name.ilike(f"%{name}%")).first()
    if not card:
        return jsonify({"found": False})
    return jsonify(
        {
            "found": True,
            "id": card.id,
            "name": card.child_name,
            "birth_date": card.birth_date.isoformat(),
            "photo_consent": card.photo_consent,
            "card_number": card.card_number,
            "phone": card.phone,
        }
    )


@app.post("/checkin")
def checkin():
    group = next_group_id()
    now = datetime.now()

    def validate_full_name(value: str) -> bool:
        parts = [p for p in value.strip().split(" ") if p]
        return len(parts) >= 2

    main_phone = request.form.get("main_phone", "").strip()
    card_order = 0
    card_group_key = f"CARD-G{group}-{now.strftime('%Y%m%d')}"

    def create_visit(prefix: str, parent_id: Optional[int] = None, inherited_phone: Optional[str] = None):
        nonlocal card_order
        name = request.form.get(f"{prefix}_name", "").strip()
        if not name:
            return None
        if not validate_full_name(name):
            flash("Trebuie sa completezi nume si prenume, nu doar un singur nume.", "error")
            return False

        phone = request.form.get(f"{prefix}_phone", "").strip() or (inherited_phone or "")
        accompanied = bool(request.form.get(f"{prefix}_accompanied"))
        at_table = bool(request.form.get(f"{prefix}_at_table"))
        status = phone if phone else ("insotit" if accompanied else "la masa" if at_table else "-")
        socks = int(request.form.get(f"{prefix}_socks") or 0)
        wants_card = bool(request.form.get(f"{prefix}_wants_card"))
        used_birthday_free = False
        loyalty_minutes = None
        loyalty_id = None

        if wants_card:
            birth = request.form.get(f"{prefix}_birth_date")
            consent = request.form.get(f"{prefix}_photo_consent") == "yes"
            if birth:
                card_order += 1
                card = LoyaltyCard(
                    card_number=f"HOP-{group:04d}-{card_order:02d}",
                    child_name=name,
                    birth_date=parse_date(birth),
                    photo_consent=consent,
                    phone=phone if phone else main_phone,
                    card_group_key=card_group_key,
                    card_order_in_group=card_order,
                )
                db.session.add(card)
                db.session.flush()
                loyalty_id = card.id

        v = Visit(
            group_id=group,
            parent_visit_id=parent_id,
            child_name=name,
            phone_or_status=status,
            checkin_time=now,
            socks_count=socks,
            used_birthday_free=used_birthday_free,
            loyalty_card_id=loyalty_id,
            loyalty_minutes_granted=loyalty_minutes,
        )
        db.session.add(v)
        return v

    parent = create_visit("main")
    if parent is False or not parent:
        cards = LoyaltyCard.query.order_by(LoyaltyCard.child_name).all()
        old_form = request.form.to_dict(flat=True)
        return render_template("checkin.html", cards=cards, old_form=old_form, sibling_prefills=extract_sibling_prefills(old_form))
    db.session.flush()

    for i in range(1, 6):
        sib_name = request.form.get(f"sibling{i}_name", "").strip()
        if sib_name:
            created = create_visit(f"sibling{i}", parent.id, inherited_phone=main_phone)
            if created is False:
                cards = LoyaltyCard.query.order_by(LoyaltyCard.child_name).all()
                old_form = request.form.to_dict(flat=True)
                return render_template("checkin.html", cards=cards, old_form=old_form, sibling_prefills=extract_sibling_prefills(old_form))

    db.session.commit()
    flash("Check-in salvat.", "success")
    return redirect(url_for("children"))


@app.route("/children")
def children():
    q = request.args.get("q", "").strip()
    start, end = current_day_range()
    query = Visit.query.filter(Visit.checkin_time >= start, Visit.checkin_time < end)
    if q:
        query = query.filter(Visit.child_name.ilike(f"%{q}%"))
    visits = query.order_by(Visit.group_id.asc(), Visit.id.asc()).all()

    grouped = {}
    for v in visits:
        grouped.setdefault(v.group_id, []).append(v)

    now = datetime.now()
    return render_template("children.html", grouped=grouped, now=now, format_duration=format_duration)


@app.post("/visit/<int:visit_id>/toggle_pause")
def toggle_pause(visit_id: int):
    v = Visit.query.get_or_404(visit_id)
    now = datetime.now()
    if v.checkout_time:
        return redirect(url_for("children"))
    if v.paused:
        v.paused = False
        if v.pause_started_at:
            mins = minutes_between(v.pause_started_at, now)
            v.paused_minutes += mins
            log = PauseLog.query.filter_by(visit_id=v.id, pause_in=None).order_by(PauseLog.id.desc()).first()
            if log:
                log.pause_in = now
        v.pause_started_at = None
    else:
        v.paused = True
        v.pause_started_at = now
        db.session.add(PauseLog(visit_id=v.id, pause_out=now))
    db.session.commit()
    return redirect(url_for("children"))


@app.post("/visit/<int:visit_id>/checkout")
def checkout(visit_id: int):
    visit = Visit.query.get_or_404(visit_id)
    group_visits = Visit.query.filter_by(group_id=visit.group_id).all()
    unfinished = [v for v in group_visits if not v.checkout_time and not v.not_stayed]
    if len(unfinished) > 1:
        flash("Nu poti face checkout individual pana nu ies toti fratii / copilul principal.", "error")
        return redirect(url_for("children"))
    return redirect(url_for("checkout_page", group_id=visit.group_id))


@app.post("/visit/<int:visit_id>/not_stayed")
def mark_not_stayed(visit_id: int):
    v = Visit.query.get_or_404(visit_id)
    v.not_stayed = True
    v.checkout_time = datetime.now()
    v.amount_paid = 0
    v.payment_method = "nu a stat"
    db.session.commit()
    return redirect(url_for("children"))


@app.route("/checkout/<int:group_id>", methods=["GET", "POST"])
def checkout_page(group_id: int):
    visits = Visit.query.filter_by(group_id=group_id).order_by(Visit.id.asc()).all()
    active = [v for v in visits if not v.not_stayed]
    if not active:
        flash("Toata grupa este marcata 'nu a stat'.", "warning")
        return redirect(url_for("children"))

    now = datetime.now()
    durations = {}
    for v in active:
        end = v.checkout_time or now
        total = minutes_between(v.checkin_time, end) - (v.paused_minutes or 0)
        durations[v.id] = max(0, total)

    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        method = request.form.get("payment_method")
        paid_cash = float(request.form.get("paid_cash") or 0)
        paid_card = float(request.form.get("paid_card") or 0)
        swords = int(request.form.get("swords") or 0)
        flowers = int(request.form.get("flowers") or 0)
        balloons_total = swords * 5 + flowers * 10

        no_payment = False
        reason = None
        for v in active:
            if v.used_birthday_free:
                no_payment = True
                reason = "Nu uita de balonul cadou de ziua de nastere"
            elif v.loyalty_minutes_granted:
                if durations[v.id] <= v.loyalty_minutes_granted:
                    no_payment = True
                    reason = "Intrare gratis folosita (fidelitate)"

        if no_payment:
            amount = 0
            paid_cash = 0
            paid_card = 0
            method = "gratis"

        for v in active:
            v.checkout_time = now
            v.amount_paid = amount
            v.payment_method = method
            v.paid_cash = paid_cash
            v.paid_card = paid_card
            v.balloons_swords = swords
            v.balloons_flowers = flowers

            if v.loyalty_card_id and not v.not_stayed:
                db.session.add(
                    LoyaltyEntry(
                        loyalty_card_id=v.loyalty_card_id,
                        visit_id=v.id,
                        visit_date=now.date(),
                        duration_minutes=durations[v.id],
                    )
                )

            if v.subscription_id:
                sub = Subscription.query.get(v.subscription_id)
                if sub:
                    sub.used_minutes += durations[v.id]
                    v.subscription_minutes_used = durations[v.id]
                    if sub.used_minutes >= sub.total_minutes:
                        sub.active = False

        if balloons_total > 0:
            db.session.add(
                ExtraPayment(
                    amount=balloons_total,
                    payment_method=method if method in {"cash", "card", "mixt"} else "cash",
                    reason="baloane",
                )
            )

        db.session.commit()
        if reason:
            flash(reason, "success")
        flash("Checkout finalizat.", "success")
        return redirect(url_for("children"))

    sorted_durations = sorted([(v.child_name, durations[v.id]) for v in active], key=lambda x: x[1], reverse=True)
    same = len(set(d for _, d in sorted_durations)) == 1
    return render_template(
        "checkout.html",
        visits=active,
        sorted_durations=sorted_durations,
        same=same,
        format_duration=format_duration,
    )


@app.post("/visit/<int:visit_id>/recheckin")
def recheckin(visit_id: int):
    v = Visit.query.get_or_404(visit_id)
    if not v.checkout_time:
        return redirect(url_for("children"))
    new_visit = Visit(
        group_id=next_group_id(),
        child_name=v.child_name,
        phone_or_status=v.phone_or_status,
        checkin_time=datetime.now(),
        loyalty_card_id=v.loyalty_card_id,
        subscription_id=v.subscription_id,
    )
    db.session.add(new_visit)
    db.session.commit()
    return redirect(url_for("children"))


@app.route("/cards")
def cards():
    q = request.args.get("q", "").strip()
    query = LoyaltyCard.query
    if q:
        query = query.filter(LoyaltyCard.child_name.ilike(f"%{q}%"))
    cards_ = query.order_by(LoyaltyCard.child_name.asc()).all()

    rows = []
    for c in cards_:
        entries = (
            LoyaltyEntry.query.filter_by(loyalty_card_id=c.id)
            .order_by(LoyaltyEntry.visit_date.desc())
            .limit(10)
            .all()
        )
        reward = compute_loyalty_reward(c.id)
        rows.append((c, entries, reward))
    return render_template("cards.html", rows=rows, format_duration=format_duration)


@app.route("/subscriptions", methods=["GET", "POST"])
def subscriptions():
    if request.method == "POST":
        mode = request.form.get("mode")
        name = request.form.get("name", "").strip()
        birth = parse_date(request.form.get("birth_date"))
        phone = request.form.get("phone", "").strip() or None
        hours = int(request.form.get("hours") or 5)
        amount = float(request.form.get("amount") or 0)
        method = request.form.get("payment_method")
        paid_cash = float(request.form.get("paid_cash") or 0)
        paid_card = float(request.form.get("paid_card") or 0)
        is_sibling = bool(request.form.get("is_sibling"))
        sibling_of = request.form.get("sibling_of", "").strip() or None

        if mode == "renew":
            sub_id = int(request.form.get("subscription_id"))
            sub = Subscription.query.get_or_404(sub_id)
            sub.total_minutes += hours * 60
            sub.active = True
        else:
            sub = Subscription(
                child_name=name,
                birth_date=birth,
                phone=phone,
                total_minutes=hours * 60,
                is_sibling=is_sibling,
                sibling_of=sibling_of,
            )
            db.session.add(sub)
            db.session.flush()

        db.session.add(
            SubscriptionPayment(
                subscription_id=sub.id,
                amount=amount,
                payment_method=method,
                paid_cash=paid_cash,
                paid_card=paid_card,
            )
        )
        flash("Abonament salvat/reinnoit.", "success")
        db.session.commit()
        return redirect(url_for("subscriptions"))

    q = request.args.get("q", "").strip()
    query = Subscription.query
    if q:
        query = query.filter(Subscription.child_name.ilike(f"%{q}%"))
    subs = query.order_by(Subscription.child_name.asc()).all()
    return render_template("subscriptions.html", subs=subs, format_duration=format_duration)


@app.post("/subscriptions/<int:sub_id>/checkin")
def checkin_subscription(sub_id: int):
    sub = Subscription.query.get_or_404(sub_id)
    now = datetime.now()
    birthday_free = False
    if is_birthday_window(sub.birth_date, now.date()) and sub.birthday_free_used_year != now.year:
        birthday_free = True
        sub.birthday_free_used_year = now.year

    visit = Visit(
        group_id=next_group_id(),
        child_name=sub.child_name,
        phone_or_status=sub.phone or "abonament",
        checkin_time=now,
        subscription_id=sub.id,
        used_birthday_free=birthday_free,
    )
    db.session.add(visit)
    db.session.commit()
    flash("Check-in pe abonament realizat.", "success")
    return redirect(url_for("children"))


@app.post("/end_of_day")
def end_of_day():
    start, end = current_day_range()
    visits = Visit.query.filter(Visit.checkout_time >= start, Visit.checkout_time < end).all()
    extras = ExtraPayment.query.filter(ExtraPayment.created_at >= start, ExtraPayment.created_at < end).all()
    sub_payments = SubscriptionPayment.query.filter(SubscriptionPayment.created_at >= start, SubscriptionPayment.created_at < end).all()

    cash = sum(v.paid_cash for v in visits) + sum(e.amount for e in extras if e.payment_method == "cash") + sum(s.paid_cash for s in sub_payments)
    card = sum(v.paid_card for v in visits) + sum(e.amount for e in extras if e.payment_method == "card") + sum(s.paid_card for s in sub_payments)
    mixed_amount = sum(v.amount_paid for v in visits if v.payment_method == "mixt") + sum(e.amount for e in extras if e.payment_method == "mixt")
    total = sum(v.amount_paid for v in visits) + sum(e.amount for e in extras) + sum(s.amount for s in sub_payments)

    return render_template("end_day.html", total=total, cash=cash, card=card, mixed_amount=mixed_amount)


@app.post("/extra_payment")
def extra_payment():
    amount = float(request.form.get("amount") or 0)
    method = request.form.get("payment_method")
    reason = request.form.get("reason")
    db.session.add(ExtraPayment(amount=amount, payment_method=method, reason=reason))
    db.session.commit()
    flash("Plata extra salvata.", "success")
    return redirect(url_for("index"))


@app.context_processor
def inject_nav():
    return {"now": datetime.now()}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)

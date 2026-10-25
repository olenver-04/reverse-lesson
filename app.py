
import streamlit as st
import sqlite3, time, uuid, hashlib
from pathlib import Path
from datetime import datetime, timezone

st.set_page_config(page_title="Урок наоборот", page_icon="🚪", layout="wide")
DB = Path("votes.db")
def connect():
    c=sqlite3.connect(DB,timeout=20,check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        code TEXT PRIMARY KEY, topic TEXT NOT NULL, pin_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'voting', winner INTEGER DEFAULT 0,
        created TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS votes (
        code TEXT NOT NULL, voter TEXT NOT NULL, choice INTEGER NOT NULL,
        PRIMARY KEY(code,voter))""")
    c.execute("""CREATE TABLE IF NOT EXISTS feedback (
        code TEXT NOT NULL, voter TEXT NOT NULL, rating INTEGER NOT NULL,
        PRIMARY KEY(code,voter))""")
    c.commit()
    return c
def pinhash(pin):
    return hashlib.sha256(pin.encode()).hexdigest()
def get_session(code):
    with connect() as c:
        return c.execute("SELECT code,topic,pin_hash,status,winner FROM sessions WHERE code=?", (code,)).fetchone()
def counts(code):
    with connect() as c:
        return [c.execute("SELECT COUNT(*) FROM votes WHERE code=? AND choice=?", (code,i)).fetchone()[0] for i in (1,2,3)]
def clean_code(v):
    return "".join(ch for ch in v.upper() if ch.isalnum())[:8]
def rerun():
    st.rerun()

st.markdown("""<style>
.stApp {background:radial-gradient(ellipse at top,#182954,#080d1f 70%);color:#f7f7ff}
.block-container {max-width:1150px;padding-top:2rem}
h1,h2,h3,p,label {color:#f5f6ff!important}
div[data-testid="stMetric"] {background:#182443;border-radius:16px;padding:14px}
div.stButton button {border-radius:14px;min-height:52px;font-weight:700}
.door {text-align:center;border:2px solid #546aab;background:linear-gradient(150deg,#344d91,#101c40);border-radius:22px;padding:24px 10px;min-height:205px;box-shadow:0 12px 35px #0005}
.door .icon {font-size:66px}
.door .title {font-size:22px;font-weight:800;margin-top:10px}
.door .desc {font-size:14px;color:#d9e3ff}
.hero {text-align:center;font-size:19px;color:#d9e3ff;padding-bottom:20px}
</style>""",unsafe_allow_html=True)
st.title("🚪 УРОК НАОБОРОТ")
st.markdown('<div class="hero">Одна тема — три пути к знаниям. Выбор за учениками!</div>',unsafe_allow_html=True)
names={1:("👁️","Посмотреть и понять","Схемы, изображения, объяснения"),2:("🎮","Поиграть и узнать","Игра, викторина, поиск ошибок"),3:("🔎","Исследовать и открыть","Гипотезы, поиск решений, обсуждение")}
params=st.query_params
code=clean_code(str(params.get("code","")))
tab1,tab2=st.tabs(["👩‍🏫 Учитель","🎒 Ученик"])
with tab1:
    st.subheader("Создать новый урок")
    with st.form("create"):
        topic=st.text_input("Тема занятия",placeholder="Например: Почему важно беречь природу?")
        pin=st.text_input("PIN учителя (минимум 4 символа)",type="password")
        create=st.form_submit_button("✨ Создать комнату",use_container_width=True)
    if create:
        if not topic.strip() or len(pin)<4:
            st.error("Введите тему и PIN длиной не менее 4 символов.")
        else:
            newcode=uuid.uuid4().hex[:6].upper()
            with connect() as c:
                c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)",
                    (newcode,topic.strip(),pinhash(pin),"voting",0,datetime.now(timezone.utc).isoformat()))
                c.commit()
            st.session_state["teacher_code"]=newcode
            st.session_state["teacher_pin"]=pin
            st.success(f"Комната создана: {newcode}")
    st.divider()
    st.subheader("Управление комнатой")
    tcode=st.text_input("Код комнаты",value=st.session_state.get("teacher_code",code),key="teacher_code_input").upper().strip()
    tpin=st.text_input("PIN комнаты",value=st.session_state.get("teacher_pin",""),type="password",key="teacher_pin_input")
    room=get_session(clean_code(tcode)) if tcode else None
    if room and pinhash(tpin)==room[2]:
        st.success(f"Тема: {room[1]}")
        st.code(room[0],language=None)
        if st.context.url:
            link=str(st.context.url).split("?")[0]+"?code="+room[0]
            st.markdown("Ссылка для учеников:")
            st.code(link,language=None)
            try:
                import qrcode
                from io import BytesIO
                img=qrcode.make(link)
                buf=BytesIO();img.save(buf,format="PNG")
                st.image(buf.getvalue(),width=230,caption="QR-код для учеников")
            except Exception:
                st.info("QR-код появится после установки qrcode.")
        values=counts(room[0])
        st.markdown("### 📊 Голоса")
        cols=st.columns(3)
        for idx,col in enumerate(cols,1):
            col.metric(names[idx][1],values[idx-1])
        st.caption(f"Всего голосов: {sum(values)}")
        a,b,c=st.columns(3)
        with a:
            if st.button("🔒 Завершить голосование",use_container_width=True):
                if sum(values)==0: st.warning("Пока нет голосов.")
                else:
                    maxcount=max(values)
                    winners=[i for i,v in enumerate(values,1) if v==maxcount]
                    if len(winners)>1:
                        st.warning("Ничья! Выберите дверь вручную ниже.")
                    else:
                        with connect() as db:
                            db.execute("UPDATE sessions SET status='closed',winner=? WHERE code=?",(winners[0],room[0]));db.commit()
                        rerun()
        with b:
            if st.button("🔄 Обновить результаты",use_container_width=True):rerun()
        with c:
            if st.button("🗑️ Сбросить голоса",use_container_width=True):
                with connect() as db:
                    db.execute("DELETE FROM votes WHERE code=?",(room[0],))
                    db.execute("DELETE FROM feedback WHERE code=?",(room[0],))
                    db.execute("UPDATE sessions SET status='voting',winner=0 WHERE code=?",(room[0],));db.commit()
                rerun()
        selected=st.selectbox("Открыть дверь вручную (например, при ничьей)",[1,2,3],format_func=lambda x:names[x][1])
        if st.button("🚪 Открыть выбранную дверь",use_container_width=True):
            with connect() as db:
                db.execute("UPDATE sessions SET status='closed',winner=? WHERE code=?",(selected,room[0]));db.commit()
            rerun()
        if room[3]=="closed":
            st.balloons()
            st.success(f"Открыта дверь: {names[room[4]][1]}")
            st.markdown("### Задание после открытия")
            st.info({
                1:"Покажите схему, изображение или короткое видео. Попросите учеников объяснить два ключевых вывода.",
                2:"Проведите мини-викторину из трёх вопросов или игру «Найди ошибку». Попросите обосновать ответы.",
                3:"Предложите проблемный вопрос. Ученики выдвигают гипотезы, ищут аргументы и представляют решение."
            }[room[4]])
            with connect() as db:
                ratings=db.execute("SELECT rating,COUNT(*) FROM feedback WHERE code=? GROUP BY rating",(room[0],)).fetchall()
            st.write("Рефлексия (1–3):",dict(ratings))
    elif tcode and tpin:
        st.warning("Комната не найдена или PIN неверный.")
with tab2:
    st.subheader("Выбери свой путь")
    scode=st.text_input("Код комнаты",value=code,key="student_code").upper().strip()
    sroom=get_session(clean_code(scode)) if scode else None
    if sroom:
        st.info(f"📚 Тема: {sroom[1]}")
        voterkey=f"voter_{sroom[0]}"
        if voterkey not in st.session_state:
            st.session_state[voterkey]=uuid.uuid4().hex
        voter=st.session_state[voterkey]
        with connect() as db:
            existing=db.execute("SELECT choice FROM votes WHERE code=? AND voter=?",(sroom[0],voter)).fetchone()
        cols=st.columns(3)
        for i,col in enumerate(cols,1):
            icon,title,desc=names[i]
            with col:
                st.markdown(f'<div class="door"><div class="icon">{icon}</div><div class="title">Дверь {i}</div><div class="title">{title}</div><div class="desc">{desc}</div></div>',unsafe_allow_html=True)
                if sroom[3]=="voting":
                    if st.button("Выбрать дверь",key=f"vote_{i}",use_container_width=True):
                        with connect() as db:
                            db.execute("INSERT INTO votes(code,voter,choice) VALUES(?,?,?) ON CONFLICT(code,voter) DO UPDATE SET choice=excluded.choice",(sroom[0],voter,i));db.commit()
                        rerun()
        if sroom[3]=="voting":
            if existing: st.success(f"Ваш голос: {names[existing[0]][1]}. До завершения голосования выбор можно изменить.")
            else: st.caption("Нажми на кнопку под одной из дверей.")
        else:
            st.success(f"🎉 Класс выбрал: {names[sroom[4]][1]}!")
            st.markdown("### 🚦 Как ты понял тему?")
            with st.form("rating"):
                rating=st.radio("Выбери ответ",["🔴 Нужна помощь","🟡 Есть вопросы","🟢 Всё понятно"],horizontal=True)
                if st.form_submit_button("Отправить"):
                    val=["🔴 Нужна помощь","🟡 Есть вопросы","🟢 Всё понятно"].index(rating)+1
                    with connect() as db:
                        db.execute("INSERT INTO feedback(code,voter,rating) VALUES(?,?,?) ON CONFLICT(code,voter) DO UPDATE SET rating=excluded.rating",(sroom[0],voter,val));db.commit()
                    st.success("Спасибо за ответ!")
    elif scode:
        st.warning("Комната не найдена. Проверь код.")
st.caption("Демо-проект для школьного конкурса • Не собирает имена учеников • Голоса сохраняются в локальной базе приложения")

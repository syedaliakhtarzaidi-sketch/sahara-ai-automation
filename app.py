import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
from pathlib import Path

st.set_page_config(page_title="Sahara Freight Intelligence", page_icon="🚚", layout="wide")
DB = Path("sahara_freight.db")

st.markdown("""
<style>
.stApp {background:#0b1220;color:#f4f7fb}
[data-testid="stSidebar"] {background:#111c2e}
h1,h2,h3,p,label,span,div {color:inherit}
[data-testid="stMetric"] {background:#142238;border:1px solid #263a55;padding:16px;border-radius:12px}
.stButton>button {background:#c7a45b;color:#101827;border:0;font-weight:700;border-radius:8px}
div[data-baseweb="input"] input, div[data-baseweb="select"] {background:#17263b;color:#fff}
</style>
""", unsafe_allow_html=True)

def conn():
    c=sqlite3.connect(DB, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS warehouses(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT NOT NULL, postcode TEXT, country TEXT, notes TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS hauliers(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, service_types TEXT, coverage TEXT, contact_email TEXT,
      phone TEXT, website TEXT, notes TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS quotes(
      id INTEGER PRIMARY KEY, quote_date TEXT NOT NULL, haulier_id INTEGER, service_type TEXT NOT NULL,
      origin TEXT NOT NULL, destination TEXT NOT NULL, pallets INTEGER, vehicle TEXT, container_size TEXT,
      base REAL DEFAULT 0, fuel REAL DEFAULT 0, tolls REAL DEFAULT 0, extras REAL DEFAULT 0,
      vat REAL DEFAULT 0, currency TEXT DEFAULT 'GBP', total REAL NOT NULL, valid_until TEXT,
      quote_ref TEXT, evidence_url TEXT, evidence_note TEXT, verification TEXT DEFAULT 'Unverified',
      verified_by TEXT, created_at TEXT, FOREIGN KEY(haulier_id) REFERENCES hauliers(id))""")
    c.commit()
    return c

db=conn()
st.title("SAHARA  /  FREIGHT INTELLIGENCE")
st.caption("Verified transport quotations • UK domestic • Northern Ireland • Republic of Ireland • FTL • Port-to-door")
st.warning("No live carrier rates are fabricated here. A quote ranks as verified only when its source evidence and confirmation details are recorded. This starter database is local to this app instance; connect persistent Supabase storage before production use.")

tabs=st.tabs(["Rate Intelligence","Add Quotation","Haulier Directory","Warehouses","Data & Export"])
with tabs[0]:
    q=pd.read_sql_query("""SELECT q.*, h.name AS haulier FROM quotes q LEFT JOIN hauliers h ON h.id=q.haulier_id""",db)
    a,b,c,d=st.columns(4)
    a.metric("Quotations",len(q))
    b.metric("Verified",int((q.verification=="Verified").sum()) if len(q) else 0)
    c.metric("Unverified",int((q.verification!="Verified").sum()) if len(q) else 0)
    d.metric("Hauliers",pd.read_sql_query("SELECT * FROM hauliers",db).shape[0])
    st.subheader("Find the three cheapest verified rates")
    service=st.selectbox("Movement type",["All","UK to UK Pallets","UK to Northern Ireland Pallets","UK to Republic of Ireland Pallets","Full Trailer Load","Port to Door Container"])
    origin=st.text_input("Collection postcode / port / town")
    dest=st.text_input("Delivery postcode / town")
    only_current=st.checkbox("Only show quotations still within validity",True)
    if len(q):
        f=q[q.verification=="Verified"].copy()
        if service!="All": f=f[f.service_type==service]
        if origin: f=f[f.origin.str.contains(origin,case=False,na=False)]
        if dest: f=f[f.destination.str.contains(dest,case=False,na=False)]
        if only_current: f=f[(f.valid_until.isna())|(f.valid_until=="")|(f.valid_until>=date.today().isoformat())]
        if len(f):
            f=f.sort_values("total").head(3)
            st.success(f"{len(f)} verified matching option(s) — ranked by total payable cost")
            cols=["haulier","service_type","origin","destination","total","currency","valid_until","quote_ref","evidence_url"]
            st.dataframe(f[cols],use_container_width=True,hide_index=True,
                         column_config={"evidence_url":st.column_config.LinkColumn("Evidence")})
        else: st.info("No verified quotations match this route yet. Add confirmed haulier quotations; unverified estimates are never promoted.")
    else: st.info("The rate database is empty. Add genuine quotations to begin ranking.")
with tabs[1]:
    st.subheader("Record a real haulier quotation")
    hs=pd.read_sql_query("SELECT id,name FROM hauliers ORDER BY name",db)
    with st.form("quote"):
        hname=st.selectbox("Haulier",["— Add haulier first —"]+([f"{r['name']} (#{r['id']})" for _,r in hs.iterrows()]))
        svc=st.selectbox("Movement type",["UK to UK Pallets","UK to Northern Ireland Pallets","UK to Republic of Ireland Pallets","Full Trailer Load","Port to Door Container"])
        x,y=st.columns(2); org=x.text_input("Collection location / port"); dst=y.text_input("Delivery location / warehouse")
        x,y,z=st.columns(3); pallets=x.number_input("Pallets",min_value=0,step=1); vehicle=y.selectbox("Vehicle",["Pallet network","7.5T","18T","26T","Artic","Other"]); cont=z.selectbox("Container",["N/A","20ft","40ft","40ft HC"])
        st.markdown("**Cost breakdown (GBP)**")
        x,y,z,w=st.columns(4); base=x.number_input("Base",min_value=0.0); fuel=y.number_input("Fuel surcharge",min_value=0.0); toll=z.number_input("Tolls",min_value=0.0); extras=w.number_input("Other charges",min_value=0.0)
        vat=st.number_input("VAT amount",min_value=0.0)
        total=base+fuel+toll+extras+vat
        st.metric("Total payable",f"£{total:,.2f}")
        x,y=st.columns(2); qdate=x.date_input("Quote date",date.today()); valid=y.date_input("Valid until",date.today())
        ref=st.text_input("Haulier quote reference")
        evidence=st.text_input("Evidence URL (email attachment / quote portal / document link)")
        note=st.text_area("Evidence / confirmation notes (email date, contact, service conditions)")
        status=st.selectbox("Verification status",["Unverified","Verified","Rejected"])
        verifier=st.text_input("Verified by / confirmation contact")
        submitted=st.form_submit_button("Save quotation")
        if submitted:
            hid=None
            if hname!="— Add haulier first —": hid=int(hname.rsplit("#",1)[1].rstrip(")"))
            if not org or not dst or total<=0: st.error("Collection, delivery and a positive total are required.")
            elif status=="Verified" and (not evidence or not ref or not note or not verifier): st.error("To mark a quote Verified, provide evidence URL, quote reference, confirmation notes and verifier/contact.")
            else:
                db.execute("""INSERT INTO quotes(quote_date,haulier_id,service_type,origin,destination,pallets,vehicle,container_size,base,fuel,tolls,extras,vat,total,valid_until,quote_ref,evidence_url,evidence_note,verification,verified_by,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(qdate.isoformat(),hid,svc,org,dst,pallets,vehicle,cont,base,fuel,toll,extras,vat,total,valid.isoformat(),ref,evidence,note,status,verifier,datetime.utcnow().isoformat()))
                db.commit(); st.success("Quotation saved."); st.rerun()
with tabs[2]:
    st.subheader("Haulier directory")
    with st.form("haulier"):
        name=st.text_input("Company name"); services=st.multiselect("Services",["UK Pallets","Northern Ireland","Republic of Ireland","FTL","Container haulage"])
        coverage=st.text_input("Coverage / regions"); email=st.text_input("Email"); phone=st.text_input("Phone"); website=st.text_input("Website"); notes=st.text_area("Notes")
        if st.form_submit_button("Add haulier"):
            if name.strip():
                db.execute("INSERT INTO hauliers(name,service_types,coverage,contact_email,phone,website,notes) VALUES(?,?,?,?,?,?,?)",(name,", ".join(services),coverage,email,phone,website,notes)); db.commit(); st.success("Haulier added."); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT name,service_types,coverage,contact_email,phone,website,notes FROM hauliers",db),use_container_width=True,hide_index=True)
with tabs[3]:
    st.subheader("Warehouse locations")
    with st.form("warehouse"):
        wn=st.text_input("Warehouse name"); addr=st.text_area("Full address"); pc=st.text_input("Postcode"); country=st.selectbox("Country",["England","Scotland","Wales","Northern Ireland","Republic of Ireland"]); memo=st.text_input("Access / delivery notes")
        if st.form_submit_button("Save warehouse"):
            if wn and addr:
                db.execute("INSERT INTO warehouses(name,address,postcode,country,notes) VALUES(?,?,?,?,?)",(wn,addr,pc,country,memo)); db.commit(); st.success("Warehouse saved."); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT name,address,postcode,country,notes FROM warehouses",db),use_container_width=True,hide_index=True)
with tabs[4]:
    st.subheader("Database export")
    for table in ["hauliers","warehouses","quotes"]:
        df=pd.read_sql_query(f"SELECT * FROM {table}",db)
        st.download_button(f"Download {table}.csv",df.to_csv(index=False).encode("utf-8"),f"sahara_{table}.csv","text/csv")
    st.caption("Production deployment should use a persistent shared database and secure credentials, not this local starter storage.")

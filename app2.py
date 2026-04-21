from flask import Flask, render_template, request, Response, redirect, url_for

import csv
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

ADSENSE_ENABLED = False
ADSENSE_CLIENT = "ca-pub-XXXXXXXXXXXXXXXX"
ADSENSE_TOP_SLOT = "1111111111"
ADSENSE_CONTENT_SLOT = "2222222222"
ADSENSE_INLINE_SLOT = "3333333333"
ADSENSE_BOTTOM_SLOT = "4444444444"
ADSENSE_LEFT_SLOT = "5555555555"
ADSENSE_RIGHT_SLOT = "6666666666"


AVERAGE_MONTHLY_CAR_COST = 6500
AVERAGE_SAVINGS_RATE = 20


def format_tl(value):
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} TL"


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def build_salary_tips(savings_rate, biggest_expense_label, ay_sonu_kalan):
    tips = []
    if savings_rate < 10:
        tips.append("Gelirinin en az %10'unu kenara koyacak otomatik bir birikim hedefi belirle.")
    if biggest_expense_label == "Kira":
        tips.append("Kira bütçeni gözden geçir; toplam gelirin %30–35 bandı daha sürdürülebilir olur.")
    elif biggest_expense_label == "Market":
        tips.append("Market giderleri için haftalık limit belirleyip toplu alışverişe geçmeyi dene.")
    elif biggest_expense_label == "Fatura":
        tips.append("Fatura kalemlerini tek tek inceleyip kullanmadığın abonelikleri kapat.")
    elif biggest_expense_label == "Diğer":
        tips.append("‘Diğer giderler’ kalemini parçalayarak hangi harcamanın bütçeyi deldiğini tespit et.")
    if ay_sonu_kalan < 0:
        tips.append("Ay sonu eksiye düştüğün için önce büyük gider kalemini küçült, sonra ek gelir alanı aç.")
    else:
        tips.append("Pozitif kalan tutarı aylık yatırım veya acil durum fonu için ayrı bir hesaba aktar.")
    return tips[:3]


def build_car_tips(km_basi_maliyet, yakit_share_pct, arac_skor):
    tips = []
    if yakit_share_pct >= 55:
        tips.append("Yakıt gideri toplam maliyetin büyük kısmını oluşturuyor; sürüş stilini ve rota planını optimize et.")
    if km_basi_maliyet > 7:
        tips.append("KM başı maliyet yüksek; daha ekonomik lastik, bakım planı veya alternatif araç tipi değerlendirmesi yap.")
    if arac_skor < 40:
        tips.append("Bu araç kullanım profili pahalı görünüyor; daha düşük tüketimli araç seçeneği uzun vadede ciddi fark yaratabilir.")
    if len(tips) < 3:
        tips.append("Sigorta ve bakım kalemlerini yılda en az bir kez karşılaştırarak toplam maliyeti aşağı çekebilirsin.")
    return tips[:3]


def save_lead(payload):
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    csv_path = data_dir / "lead_requests.csv"
    fieldnames = [
        "timestamp", "source", "name", "email", "phone", "goal", "summary", "page"
    ]
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({key: payload.get(key, "") for key in fieldnames})


@app.route("/robots.txt")
def robots_txt():
    content = """User-agent: *
Allow: /

Sitemap: /sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://finanskral.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(xml, mimetype="application/xml")


@app.route("/", methods=["GET", "POST"])
def home():
    maas_sonuc = None
    arac_sonuc = None
    active_tab = request.args.get("tab", "maas")
    lead_status = request.args.get("lead")
    lead_source = request.args.get("source")

    site_url = request.url_root.rstrip("/") + "/"
    page_title = "Maaş Gelir Gider ve Araç Kullanım Maliyeti Hesaplama | FinansKral"
    meta_description = (
        "Maaş gelir gider hesaplama, net maaş analizi, araç kullanım maliyeti ve "
        "yakıt gideri hesaplama aracı. Türkiye için pratik finans hesaplama platformu."
    )

    fuel_prices = {
        "istanbul_avrupa": {
            "label": "İstanbul Avrupa",
            "gasoline": 62.70,
            "diesel": 71.59,
            "lpg": 34.99,
        },
        "ankara": {
            "label": "Ankara",
            "gasoline": 63.67,
            "diesel": 72.71,
            "lpg": 34.87,
        },
        "izmir": {
            "label": "İzmir",
            "gasoline": 63.94,
            "diesel": 72.99,
            "lpg": 34.79,
        },
    }

    selected_city = request.form.get("fuel_city", "istanbul_avrupa")
    if selected_city not in fuel_prices:
        selected_city = "istanbul_avrupa"

    selected_fuel_data = fuel_prices[selected_city]
    fuel_note = "Yakıt fiyatları şehir ve istasyona göre değişebilir."

    maas_form = {
        "brut": "",
        "yemek": "",
        "yol": "",
        "kira": "",
        "fatura": "",
        "market": "",
        "diger": "",
    }

    arac_form = {
        "fuel_city": selected_city,
        "km": "",
        "tuketim": "",
        "yakit_tipi": "gasoline",
        "yakit": "",
        "sigorta": "",
        "bakim": "",
        "mtv": "",
        "manuel_yakit": "off",
    }

    if request.method == "POST":
        form_tipi = request.form.get("form_type")

        if form_tipi == "maas":
            active_tab = "maas"

            maas_form["brut"] = request.form.get("brut", "")
            maas_form["yemek"] = request.form.get("yemek", "")
            maas_form["yol"] = request.form.get("yol", "")
            maas_form["kira"] = request.form.get("kira", "")
            maas_form["fatura"] = request.form.get("fatura", "")
            maas_form["market"] = request.form.get("market", "")
            maas_form["diger"] = request.form.get("diger", "")

            brut = safe_float(request.form.get("brut"))
            yemek = safe_float(request.form.get("yemek"))
            yol = safe_float(request.form.get("yol"))
            kira = safe_float(request.form.get("kira"))
            fatura = safe_float(request.form.get("fatura"))
            market = safe_float(request.form.get("market"))
            diger = safe_float(request.form.get("diger"))

            sgk = brut * 0.14
            issizlik = brut * 0.01
            vergi_matrahi = brut - sgk - issizlik
            vergi = vergi_matrahi * 0.15

            toplam_kesinti = sgk + issizlik + vergi
            yan_haklar = yemek + yol
            net_maas = brut - toplam_kesinti + yan_haklar
            isveren_sgk = brut * 0.155
            isveren_maliyeti = brut + isveren_sgk + yemek + yol

            total_expenses = {
                "Kira": kira,
                "Fatura": fatura,
                "Market": market,
                "Diğer": diger,
            }
            toplam_gider = sum(total_expenses.values())
            ay_sonu_kalan = net_maas - toplam_gider
            yillik_gider = toplam_gider * 12
            yillik_kalan = ay_sonu_kalan * 12
            savings_rate = (ay_sonu_kalan / net_maas * 100) if net_maas > 0 else 0
            gider_orani = (toplam_gider / net_maas * 100) if net_maas > 0 else 100
            maas_skor = round(clamp(100 - gider_orani, 0, 100))
            biggest_expense_label, biggest_expense_value = max(total_expenses.items(), key=lambda item: item[1])
            benchmark_gap = ay_sonu_kalan - (net_maas * (AVERAGE_SAVINGS_RATE / 100))

            if maas_skor >= 70:
                maas_skor_yorum = "Güçlü denge"
            elif maas_skor >= 40:
                maas_skor_yorum = "Orta denge"
            else:
                maas_skor_yorum = "Zayıf denge"

            if benchmark_gap >= 0:
                benchmark_text = "Ortalama birikim seviyesinin üzerindesin"
            else:
                benchmark_text = "Ortalama birikim seviyesinin altındasın"

            salary_tips = build_salary_tips(savings_rate, biggest_expense_label, ay_sonu_kalan)

            maas_sonuc = {
                "brut_maas": format_tl(brut),
                "sgk": format_tl(sgk),
                "issizlik": format_tl(issizlik),
                "vergi_matrahi": format_tl(vergi_matrahi),
                "vergi": format_tl(vergi),
                "toplam_kesinti": format_tl(toplam_kesinti),
                "yan_haklar": format_tl(yan_haklar),
                "maastan_kalan": format_tl(brut - toplam_kesinti),
                "isveren_sgk": format_tl(isveren_sgk),
                "isveren_maliyeti": format_tl(isveren_maliyeti),
                "net_maas": format_tl(net_maas),
                "kira": format_tl(kira),
                "fatura": format_tl(fatura),
                "market": format_tl(market),
                "diger": format_tl(diger),
                "toplam_gider": format_tl(toplam_gider),
                "ay_sonu_kalan": format_tl(ay_sonu_kalan),
                "ay_sonu_kalan_raw": ay_sonu_kalan,
                "net_maas_raw": net_maas,
                "toplam_gider_raw": toplam_gider,
                "maas_skor": maas_skor,
                "maas_skor_yorum": maas_skor_yorum,
                "yillik_gider": format_tl(yillik_gider),
                "yillik_kalan": format_tl(yillik_kalan),
                "savings_rate": round(savings_rate, 1),
                "biggest_expense_label": biggest_expense_label,
                "biggest_expense_value": format_tl(biggest_expense_value),
                "biggest_expense_raw": biggest_expense_value,
                "benchmark_gap": format_tl(benchmark_gap),
                "benchmark_gap_raw": benchmark_gap,
                "benchmark_text": benchmark_text,
                "tips": salary_tips,
                "expense_labels": list(total_expenses.keys()),
                "expense_values": list(total_expenses.values()),
            }

        elif form_tipi == "arac":
            active_tab = "arac"

            arac_form["fuel_city"] = request.form.get("fuel_city", "istanbul_avrupa")
            arac_form["km"] = request.form.get("km", "")
            arac_form["tuketim"] = request.form.get("tuketim", "")
            arac_form["yakit_tipi"] = request.form.get("yakit_tipi", "gasoline")
            arac_form["yakit"] = request.form.get("yakit", "")
            arac_form["sigorta"] = request.form.get("sigorta", "")
            arac_form["bakim"] = request.form.get("bakim", "")
            arac_form["mtv"] = request.form.get("mtv", "")
            arac_form["manuel_yakit"] = request.form.get("manuel_yakit", "off")

            selected_city = arac_form["fuel_city"]
            if selected_city not in fuel_prices:
                selected_city = "istanbul_avrupa"
                arac_form["fuel_city"] = selected_city

            selected_fuel_data = fuel_prices[selected_city]

            km = safe_float(request.form.get("km"))
            tuketim = safe_float(request.form.get("tuketim"))
            yakit = safe_float(request.form.get("yakit"))
            sigorta = safe_float(request.form.get("sigorta"))
            bakim = safe_float(request.form.get("bakim"))
            mtv = safe_float(request.form.get("mtv"))

            aylik_yakit = (km / 100) * tuketim * yakit
            aylik_sigorta = sigorta / 12
            aylik_bakim = bakim / 12
            aylik_mtv = mtv / 12
            yearly_total = sigorta + bakim + mtv + (aylik_yakit * 12)
            aylik_toplam = aylik_yakit + aylik_sigorta + aylik_bakim + aylik_mtv
            km_basi_maliyet = aylik_toplam / km if km > 0 else 0
            arac_skor = round(clamp(100 - (km_basi_maliyet * 10), 0, 100))
            vehicle_costs = {
                "Yakıt": aylik_yakit,
                "Sigorta": aylik_sigorta,
                "Bakım": aylik_bakim,
                "MTV": aylik_mtv,
            }
            biggest_car_cost_label, biggest_car_cost_value = max(vehicle_costs.items(), key=lambda item: item[1])
            yakit_share_pct = (aylik_yakit / aylik_toplam * 100) if aylik_toplam > 0 else 0
            benchmark_diff = aylik_toplam - AVERAGE_MONTHLY_CAR_COST
            cheaper_if_reduce_km = aylik_toplam - (((km * 0.85) / 100) * tuketim * yakit + aylik_sigorta + aylik_bakim + aylik_mtv)
            cheaper_if_better_efficiency = aylik_toplam - ((km / 100) * (tuketim * 0.8) * yakit + aylik_sigorta + aylik_bakim + aylik_mtv)

            if arac_skor >= 70:
                arac_skor_yorum = "Verimli kullanım"
            elif arac_skor >= 40:
                arac_skor_yorum = "Orta maliyet"
            else:
                arac_skor_yorum = "Yüksek maliyet"

            if benchmark_diff <= 0:
                benchmark_text = "Türkiye ortalama araç giderinin altında görünüyorsun"
            else:
                benchmark_text = "Türkiye ortalama araç giderinin üzerindesin"

            car_tips = build_car_tips(km_basi_maliyet, yakit_share_pct, arac_skor)

            arac_sonuc = {
                "aylik_yakit": format_tl(aylik_yakit),
                "aylik_sigorta": format_tl(aylik_sigorta),
                "aylik_bakim": format_tl(aylik_bakim),
                "aylik_mtv": format_tl(aylik_mtv),
                "aylik_toplam": format_tl(aylik_toplam),
                "km_basi_maliyet": format_tl(km_basi_maliyet),
                "aylik_yakit_raw": aylik_yakit,
                "aylik_sigorta_raw": aylik_sigorta,
                "aylik_bakim_raw": aylik_bakim,
                "aylik_mtv_raw": aylik_mtv,
                "aylik_toplam_raw": aylik_toplam,
                "arac_skor": arac_skor,
                "arac_skor_yorum": arac_skor_yorum,
                "yearly_total": format_tl(yearly_total),
                "benchmark_diff": format_tl(benchmark_diff),
                "benchmark_diff_raw": benchmark_diff,
                "benchmark_text": benchmark_text,
                "biggest_cost_label": biggest_car_cost_label,
                "biggest_cost_value": format_tl(biggest_car_cost_value),
                "tips": car_tips,
                "save_reduce_km": format_tl(cheaper_if_reduce_km),
                "save_better_efficiency": format_tl(cheaper_if_better_efficiency),
                "cost_labels": list(vehicle_costs.keys()),
                "cost_values": list(vehicle_costs.values()),
            }

    return render_template(
        "index2.html",
        maas_sonuc=maas_sonuc,
        arac_sonuc=arac_sonuc,
        maas_form=maas_form,
        arac_form=arac_form,
        active_tab=active_tab,
        fuel_prices=fuel_prices,
        fuel_note=fuel_note,
        selected_city=selected_city,
        selected_fuel_data=selected_fuel_data,
        adsense_enabled=ADSENSE_ENABLED,
        adsense_client=ADSENSE_CLIENT,
        adsense_top_slot=ADSENSE_TOP_SLOT,
        adsense_content_slot=ADSENSE_CONTENT_SLOT,
        adsense_inline_slot=ADSENSE_INLINE_SLOT,
        adsense_bottom_slot=ADSENSE_BOTTOM_SLOT,
        adsense_left_slot=ADSENSE_LEFT_SLOT,
        adsense_right_slot=ADSENSE_RIGHT_SLOT,
        site_url=site_url,
        page_title=page_title,
        meta_description=meta_description,
        lead_status=lead_status,
        lead_source=lead_source,
    )


@app.route("/capture-lead", methods=["POST"])
def capture_lead():
    source = request.form.get("source", "maas")
    save_lead({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "name": request.form.get("lead_name", "").strip(),
        "email": request.form.get("lead_email", "").strip(),
        "phone": request.form.get("lead_phone", "").strip(),
        "goal": request.form.get("lead_goal", "").strip(),
        "summary": request.form.get("lead_summary", "").strip(),
        "page": request.url_root.rstrip("/") + "/",
    })
    return redirect(url_for("home", lead="success", source=source, tab=source))

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)

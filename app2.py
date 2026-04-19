from flask import Flask, render_template, request, Response

app = Flask(__name__)

ADSENSE_ENABLED = False
ADSENSE_CLIENT = "ca-pub-XXXXXXXXXXXXXXXX"
ADSENSE_TOP_SLOT = "1111111111"
ADSENSE_CONTENT_SLOT = "2222222222"
ADSENSE_INLINE_SLOT = "3333333333"
ADSENSE_BOTTOM_SLOT = "4444444444"
ADSENSE_LEFT_SLOT = "5555555555"
ADSENSE_RIGHT_SLOT = "6666666666"


def format_tl(value):
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} TL"


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


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
    active_tab = "maas"

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
            "lpg": 34.99
        },
        "ankara": {
            "label": "Ankara",
            "gasoline": 63.67,
            "diesel": 72.71,
            "lpg": 34.87
        },
        "izmir": {
            "label": "İzmir",
            "gasoline": 63.94,
            "diesel": 72.99,
            "lpg": 34.79
        }
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
        "diger": ""
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
        "manuel_yakit": "off"
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

            brut = float(request.form.get("brut", 0) or 0)
            yemek = float(request.form.get("yemek", 0) or 0)
            yol = float(request.form.get("yol", 0) or 0)
            kira = float(request.form.get("kira", 0) or 0)
            fatura = float(request.form.get("fatura", 0) or 0)
            market = float(request.form.get("market", 0) or 0)
            diger = float(request.form.get("diger", 0) or 0)

            sgk = brut * 0.14
            issizlik = brut * 0.01
            vergi_matrahi = brut - sgk - issizlik
            vergi = vergi_matrahi * 0.15

            toplam_kesinti = sgk + issizlik + vergi
            yan_haklar = yemek + yol
            net_maas = brut - toplam_kesinti + yan_haklar
            isveren_sgk = brut * 0.155
            isveren_maliyeti = brut + isveren_sgk + yemek + yol

            toplam_gider = kira + fatura + market + diger
            ay_sonu_kalan = net_maas - toplam_gider

            gider_orani = (toplam_gider / net_maas * 100) if net_maas > 0 else 100
            maas_skor = round(clamp(100 - gider_orani, 0, 100))

            if maas_skor >= 70:
                maas_skor_yorum = "Güçlü denge"
            elif maas_skor >= 40:
                maas_skor_yorum = "Orta denge"
            else:
                maas_skor_yorum = "Zayıf denge"

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
                "maas_skor_yorum": maas_skor_yorum
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

            km = float(request.form.get("km", 0) or 0)
            tuketim = float(request.form.get("tuketim", 0) or 0)
            yakit = float(request.form.get("yakit", 0) or 0)
            sigorta = float(request.form.get("sigorta", 0) or 0)
            bakim = float(request.form.get("bakim", 0) or 0)
            mtv = float(request.form.get("mtv", 0) or 0)

            aylik_yakit = (km / 100) * tuketim * yakit
            aylik_sigorta = sigorta / 12
            aylik_bakim = bakim / 12
            aylik_mtv = mtv / 12
            aylik_toplam = aylik_yakit + aylik_sigorta + aylik_bakim + aylik_mtv
            km_basi_maliyet = aylik_toplam / km if km > 0 else 0

            arac_skor = round(clamp(100 - (km_basi_maliyet * 100), 0, 100))

            if arac_skor >= 70:
                arac_skor_yorum = "Verimli kullanım"
            elif arac_skor >= 40:
                arac_skor_yorum = "Orta maliyet"
            else:
                arac_skor_yorum = "Yüksek maliyet"

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
                "arac_skor_yorum": arac_skor_yorum
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
        meta_description=meta_description
    )


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

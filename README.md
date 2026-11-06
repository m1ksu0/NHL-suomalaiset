# Suomalaiset NHL:ssä

**Avaa sivu: https://m1ksu0.github.io/NHL-suomalaiset/**

Sivu päivittyy automaattisesti joka päivä klo 07:00 UTC (09:00 Suomen talviaikaa). Repo: https://github.com/m1ksu0/NHL-suomalaiset

Hakee suomalaisten NHL-pelaajien tiedot NHL:n epävirallisesta rajapinnasta ja tekee niistä verkkosivun, jonka GitHub Actions päivittää joka päivä.

Sivulla on:
- **Tulokset:** kaksi edellistä NHL-pelipäivää, ottelujen tulokset ja suomalaisten pelaajien luvut (kenttäpelaajilta maalit, syötöt, pisteet, plusmiinus ja peliaika; maalivahdeilta torjunnat, torjunta-% ja päästetyt maalit).
- **Tulossa:** seuraavan 7 päivän ottelut, jotka alkavat Suomen aikaa klo 18.00–23.00 (molemmat mukana), ja joukkueiden suomalaiset pelaajat.
- **Kausitilastot:** kaikki suomalaiset kenttäpelaajat ja maalivahdit (runkosarja).

## Tiedostot

| Tiedosto | Tehtävä |
|---|---|
| `fetch_data.py` | Hakee tiedot ja kirjoittaa `data.json`:in |
| `build_html.py` | Tekee `data.json`:ista `site/index.html`:n |
| `tests/test_fetch.py` | Yksikkötestit (aikaikkuna, kausi-id, suomalaisten poiminta) |
| `.github/workflows/update.yml` | Ajaa haun ja julkaisee sivun GitHub Pagesiin joka päivä klo 07:00 UTC |

`data.json` ja `site/` syntyvät ajossa, eikä niitä tallenneta repoon.

## Ajo paikallisesti

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python fetch_data.py
python build_html.py
```

Sivu on tiedostossa `site/index.html`. Julkaistu versio on osoitteessa https://m1ksu0.github.io/NHL-suomalaiset/. Testit: `python -m unittest discover -s tests`.

## Julkaisu GitHub Pagesiin (kerran)

1. Luo julkinen GitHub-repo ja pushaa koodi (`main`-haara).
2. Repossa: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions → Päivitä suomalaiset NHL:ssä → Run workflow**.
4. Sivu aukeaa osoitteessa https://m1ksu0.github.io/NHL-suomalaiset/ (yleisesti `https://<käyttäjä>.github.io/<repo>/`).

Tuoreen tilanteen saa milloin tahansa ajamalla työnkulun käsin (vaihe 3).

Tarkempi ohje: vaultin muistiinpano `GitHub Actions - ajastettu päivitys ja Pages`.

## Huomioita

- **Rajapinta on epävirallinen** (`api-web.nhle.com` ja `api.nhle.com/stats/rest`). NHL voi muuttaa sitä ilman ennakkoa. Jos kausitilastojen haku epäonnistuu, ajo kaatuu ja vanha sivu jää voimaan. Yksittäisen ottelun haun epäonnistuminen näkyy vain varoituksena sivulla.
- **Pelipäivä** tarkoittaa NHL:n omaa pelipäivää (ottelun `gameDate`), joten länsirannikon myöhäinen peli kuuluu samaan päivään kuin muutkin saman illan ottelut. Ajat näytetään Suomen aikaa.
- **Tulossa-osion suomalaiset** poimitaan joukkueen nykyisestä kokoonpanosta (syntymämaa Suomi). Kokoonpanoa ei ole vahvistettu, joten loukkaantunut pelaaja voi näkyä listalla.
- **Cron on UTC:ssä.** Kesäaikana ajo tapahtuu tunnin myöhemmin Suomen aikaa (klo 10.00).
- Kausitilastot ovat vain runkosarjasta (`gameTypeId=2`). Pudotuspelien tulokset näkyvät Tulokset-osiossa, mutta eivät kausitilastoissa.
- GitHub pysäyttää ajastukset, jos julkisessa repossa ei ole aktiivisuutta 60 päivään. Työnkulun viimeinen vaihe (**Keepalive**) tekee tyhjän commitin, kun viimeisin commit on yli 45 päivää vanha, joten se commitoi noin 6 viikon välein. Jos ajastus silti pysähtyy, käynnistä se ajamalla työnkulku käsin (Actions → Run workflow).

# Reports partner endpoints

Base: `https://api.gerami.online/v1/reports`
Auth: `X-API-Key` for a key on partner `reports`.
All GET. Served by [`app/partners/reports/`](../../app/partners/reports/).

This is a **reporting** feed for senior management (not operational). It is meant
to be fetched by an **Airflow DAG** every ~2 minutes and posted to a private
Telegram channel — PriceHub returns both the structured data **and** a
ready-to-post Persian message; it does not schedule or send anything itself.

---

## GET /v1/reports/platform-compare

Competitive snapshot for one asset: where Gerami stands versus the other
platforms, ranked by **user-buy price** (the platform's sell/ask price, فروش —
what a customer pays to buy), high→low.

**Scope:** `reports:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | **required** | `gold-18k` \| `silver-999` \| `copper` (any asset slug) |
| `currency` | string | `IRT` | currency code |
| `max_age_seconds` | int (30–3600) | `180` | exclude sources not updated within this window (we crawl every ~120s) |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/reports/platform-compare?asset=gold-18k&currency=IRT"
```

### `data`

```jsonc
{
  "asset": { "slug": "gold-18k", "symbol": "GOLD_18K", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
  "currency": { "code": "IRT", "title_fa": "تومان" },
  "as_of": "2026-07-19T15:32:25+00:00",
  "params": { "max_age_seconds": 180, "sort_by": "user_buy_price (ask/فروش)" },

  "gerami": {
    "present": true,
    "rank": 12, "of": 17,
    "user_buy_price": "18777477.00",
    "cheaper_than_competitors": 11, "competitors": 16, "cheaper_than_pct": 69,
    "position": "cheaper",
    "vs_market": {
      "diff_from_mean": "-42000.00", "diff_pct_from_mean": -0.22,
      "diff_from_median": "-35000.00"
    },
    "vs_cheapest": "39477.00", "vs_most_expensive": "-194886.00",
    "crawled_at": "2026-07-19T15:32:02+00:00", "age_seconds": 41
  },

  "market": {                       // over COMPETITORS' user-buy price (Gerami excluded)
    "count": 16,
    "mean": "18819000.00", "median": "18812000.00", "stdev": "41250.10",
    "mean_2sigma": "18815000.00", "count_2sigma": 15,
    "mean_3sigma": "18819000.00", "count_3sigma": 16,
    "min": { "price": "18738000.00", "source": "milligold", "source_fa": "میلی‌گلد" },
    "max": { "price": "18972363.00", "source": "goldika",   "source_fa": "گلدیکا" },
    "spread": "234363.00",
    "excluded_stale": [ { "slug": "invi", "source_fa": "اینوی", "age_seconds": 250, "reason": "stale" } ]
  },

  "leaderboard": [                  // every fresh source incl. Gerami, by user-buy price desc
    { "rank": 1,  "source": "goldika", "source_fa": "گلدیکا", "user_buy_price": "18972363.00", "diff_from_gerami": "+194886.00", "is_gerami": false },
    { "rank": 12, "source": "gerami",  "source_fa": "گرمی",   "user_buy_price": "18777477.00", "diff_from_gerami": null,          "is_gerami": true  }
  ],

  "message": "📊 گزارش رقابتی قیمت — طلای ۱۸ عیار …"   // ready-to-post Persian Telegram text
}
```

### The Persian message (`data.message`)

A ready-to-post Telegram message (Jalali date, Tehran time, Persian digits):

```
📊 گزارش رقابتی قیمت — طلای ۱۸ عیار (قیمت خرید کاربر)
🕓 ۱۴۰۵/۰۴/۲۸ — ۱۹:۰۲

🟢 جایگاه گرمی
رتبه ۱۲ از ۱۷ · ارزان‌تر از ۶۹٪ رقبا
قیمت خرید کاربر: ۱۸٬۷۷۷٬۴۷۷ تومان
اختلاف با میانگین بازار: −۴۲٬۰۰۰ (−۰٫۲۲٪) ⬇️ ارزان‌تر ✅
اختلاف با میانه: −۳۵٬۰۰۰

📈 خلاصهٔ بازار (بدون گرمی)
میانگین: ۱۸٬۸۱۹٬۰۰۰ · میانه: ۱۸٬۸۱۲٬۰۰۰
میانگین بدون پرت ۲σ: ۱۸٬۸۱۵٬۰۰۰
کمینه: ۱۸٬۷۳۸٬۰۰۰ (میلی‌گلد)
بیشینه: ۱۸٬۹۷۲٬۳۶۳ (گلدیکا)
اسپرد بازار: ۲۳۴٬۳۶۳ · به‌روز: ۱۶ پلتفرم

🏷 رتبه‌بندی قیمت خرید کاربر (زیاد→کم):
۱. گلدیکا — ۱۸٬۹۷۲٬۳۶۳ (+۱۹۴٬۸۸۶)
…
⭐ ۱۲. گرمی — ۱۸٬۷۷۷٬۴۷۷
…
```

Field notes:
- **user-buy price** = the source's clean ask/فروش (the `-1` sentinel stripped; a
  single-rate source's price counts as its ask).
- **`gerami.cheaper_than_pct`** = share of competitors more expensive than Gerami
  (higher = Gerami is cheaper for buyers). `position` is `cheaper` or
  `more_expensive` vs the market mean.
- **`market`** excludes Gerami and only counts fresh sources; `excluded_stale`
  lists those dropped for being older than `max_age_seconds`.
- If Gerami has no fresh quote, `gerami` is `{ "present": false }` and the message
  says so.

## Consuming from the Telegram DAG

The DAG just needs to GET this endpoint and post `data.message`:
```python
r = requests.get(URL, headers={"X-API-Key": KEY}, params={"asset": "gold-18k", "currency": "IRT"})
text = r.json()["data"]["message"]
# send `text` to the private channel (through the v2ray proxy)
```

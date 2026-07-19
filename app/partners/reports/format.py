"""Persian formatting helpers + the Telegram-ready message builder.

Dependency-free: Persian digits, a thousands separator, a Gregorian→Jalali
conversion, and Tehran local time (fixed UTC+3:30 — Iran no longer observes DST,
so we avoid needing a tz database in the slim image).
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_TEHRAN_OFFSET = timedelta(hours=3, minutes=30)  # Iran Standard Time, no DST


def fa_digits(s: str) -> str:
    return s.translate(_FA_DIGITS)


def fa_int(x: Any) -> str:
    """Round to an integer and render with ٬ separators + Persian digits."""
    if x is None:
        return "—"
    n = int(round(float(x)))
    s = f"{abs(n):,}".replace(",", "٬")
    return ("−" if n < 0 else "") + fa_digits(s)


def fa_signed(x: Any) -> str:
    """Like fa_int but always with an explicit +/− sign."""
    if x is None:
        return "—"
    n = int(round(float(x)))
    s = f"{abs(n):,}".replace(",", "٬")
    return ("−" if n < 0 else "+") + fa_digits(s)


def fa_pct(x: Any, dp: int = 2) -> str:
    if x is None:
        return "—"
    sign = "−" if float(x) < 0 else "+"
    return sign + fa_digits(f"{abs(float(x)):.{dp}f}") + "٪"


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Standard Gregorian→Jalali (Solar Hijri) conversion."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
        - 80 + gd + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def tehran_stamp(now_utc: datetime) -> str:
    """'۱۴۰۵/۰۴/۲۸ — ۱۹:۰۲' in Tehran local time (UTC+3:30)."""
    t = now_utc.astimezone(timezone.utc) + _TEHRAN_OFFSET
    jy, jm, jd = gregorian_to_jalali(t.year, t.month, t.day)
    date = fa_digits(f"{jy:04d}/{jm:02d}/{jd:02d}")
    clock = fa_digits(f"{t.hour:02d}:{t.minute:02d}")
    return f"{date} — {clock}"


def build_message(report: dict[str, Any], now_utc: datetime) -> str:
    """Render the competitive report as a Telegram-ready Persian message."""
    asset_fa = report["asset"].get("title_fa", report["asset"].get("slug", ""))
    lines: list[str] = []
    lines.append(f"📊 گزارش رقابتی قیمت — {asset_fa} (قیمت خرید کاربر)")
    lines.append(f"🕓 {tehran_stamp(now_utc)}")
    lines.append("")

    g = report.get("gerami")
    if g and g.get("present"):
        vm = g["vs_market"]
        arrow = "⬇️" if g["position"] == "cheaper" else "⬆️"
        verdict = "ارزان‌تر ✅" if g["position"] == "cheaper" else "گران‌تر ⚠️"
        lines.append("🟢 جایگاه گرمی")
        lines.append(
            f"رتبه {fa_digits(str(g['rank']))} از {fa_digits(str(g['of']))}"
            f" · ارزان‌تر از {fa_digits(str(g['cheaper_than_pct']))}٪ رقبا"
        )
        lines.append(f"قیمت خرید کاربر: {fa_int(g['user_buy_price'])} تومان")
        lines.append(
            f"اختلاف با میانگین بازار: {fa_signed(vm['diff_from_mean'])}"
            f" ({fa_pct(vm['diff_pct_from_mean'])}) {arrow} {verdict}"
        )
        lines.append(f"اختلاف با میانه: {fa_signed(vm['diff_from_median'])}")
    else:
        lines.append("🟠 جایگاه گرمی: دادهٔ به‌روزِ گرمی در دسترس نیست (کهنه یا بدون قیمت).")
    lines.append("")

    m = report.get("market")
    if m and m.get("count"):
        lines.append("📈 خلاصهٔ بازار (بدون گرمی)")
        lines.append(f"میانگین: {fa_int(m['mean'])} · میانه: {fa_int(m['median'])}")
        lines.append(f"میانگین بدون پرت ۲σ: {fa_int(m['mean_2sigma'])}")
        lines.append(f"کمینه: {fa_int(m['min']['price'])} ({m['min']['source_fa']})")
        lines.append(f"بیشینه: {fa_int(m['max']['price'])} ({m['max']['source_fa']})")
        lines.append(
            f"اسپرد بازار: {fa_int(m['spread'])} · به‌روز: {fa_digits(str(m['count']))} پلتفرم"
        )
    lines.append("")

    lb = report.get("leaderboard") or []
    if lb:
        lines.append("🏷 رتبه‌بندی قیمت خرید کاربر (زیاد→کم):")
        for row in lb:
            star = "⭐ " if row["is_gerami"] else ""
            diff = "" if row["is_gerami"] else f" ({fa_signed(row['diff_from_gerami'])})"
            lines.append(
                f"{star}{fa_digits(str(row['rank']))}. {row['source_fa']} — "
                f"{fa_int(row['user_buy_price'])}{diff}"
            )

    stale = (report.get("market") or {}).get("excluded_stale") or []
    if stale:
        names = "، ".join(s["source_fa"] for s in stale)
        lines.append("")
        lines.append(f"⏱ حذف‌شده به‌خاطر کهنگی (>۳ دقیقه): {names}")

    return "\n".join(lines)


def _metal_emoji(slug: str) -> str:
    if slug.startswith(("gold", "coin")):
        return "🥇"
    if slug.startswith("silver"):
        return "🥈"
    if slug.startswith("copper"):
        return "🥉"
    return "•"


def _esc(s: Any) -> str:
    """HTML-escape a dynamic value for Telegram parse_mode=HTML."""
    return html.escape(str(s), quote=False)


def build_compact(report: dict[str, Any]) -> str:
    """A short, header-less HTML block for one asset — safe to stack several
    under one header without cluttering (Telegram parse_mode=HTML).

    Three lines: metal title, Gerami's position, one-line market summary.
    """
    a = report["asset"]
    slug = a.get("slug", "")
    fa = _esc(a.get("title_fa", slug))
    lines = [f"{_metal_emoji(slug)} <b>{fa}</b>"]

    g = report.get("gerami")
    m = report.get("market")
    if g and g.get("present"):
        vm = g["vs_market"]
        arrow = "⬇️" if g["position"] == "cheaper" else "⬆️"
        verdict = "ارزان‌تر" if g["position"] == "cheaper" else "گران‌تر"
        lines.append(
            f"گرمی: رتبه {fa_digits(str(g['rank']))}/{fa_digits(str(g['of']))} · "
            f"<b>{fa_int(g['user_buy_price'])}</b> ت · {arrow} {verdict} از میانگین "
            f"({fa_pct(vm['diff_pct_from_mean'])})"
        )
    else:
        lines.append("گرمی: دادهٔ به‌روز ندارد ⏱")

    if m and m.get("count"):
        lines.append(
            f"بازار: میانه {fa_int(m['median'])} · "
            f"کف {_esc(m['min']['source_fa'])} | سقف {_esc(m['max']['source_fa'])}"
        )
    return "\n".join(lines)


def _num_en(x: Any) -> str:
    """Latin digits + thousands commas, for the aligned monospace table. None→0."""
    if x is None:
        return "0"
    return f"{int(round(float(x))):,}"


def _metal_dot(slug: str) -> str:
    if slug.startswith(("gold", "coin")):
        return "🟡"
    if slug.startswith("silver"):
        return "⚪"
    if slug.startswith("copper"):
        return "🟠"
    return "▫️"


def build_table(report: dict[str, Any]) -> str:
    """One full per-metal message: a Persian ceiling/Gerami/floor summary + a
    monospace table of ALL platforms (Buy / Sell / Spread), sorted by user-buy
    price, with Gerami's row flagged 🔸 (marker sits to the LEFT of the box so the
    columns stay perfectly aligned — emojis are ~2 cells wide in monospace)."""
    a = report["asset"]
    slug = a.get("slug", "")
    fa = _esc(a.get("title_fa", slug))
    stamp = report.get("stamp_fa", "")
    lb = report.get("leaderboard") or []
    g = report.get("gerami")

    # ── Header + ceiling / Gerami / floor summary ──
    out = [f"{_metal_dot(slug)} <b>{fa}</b>", f"🕓 زمان: {stamp}", ""]
    # Summary is from the USER's buy side (what the customer pays to buy = the
    # platform's sell/ask). The leaderboard is already sorted by it, high→low.
    # 🔺 = ceiling, 🔻 = floor (the emoji says it — no سقف/کف label needed).
    if lb:
        top, bottom = lb[0], lb[-1]
        out.append(f"🔺 {_esc(top['source_fa'])} — {fa_int(top['user_buy_price'])}")
        if g and g.get("present"):
            out.append(
                f"🔸 گرمی: {fa_int(g['user_buy_price'])} · "
                f"رتبه {fa_digits(str(g['rank']))} از {fa_digits(str(g['of']))}"
            )
        else:
            out.append("🔸 گرمی: دادهٔ به‌روز ندارد")
        out.append(f"🔻 {_esc(bottom['source_fa'])} — {fa_int(bottom['user_buy_price'])}")
    else:
        out.append("دادهٔ به‌روزی برای این دارایی نیست.")

    # ── Monospace table (Latin, aligned): Market | Buy | Sell ──
    # From the USER's side: Buy = user pays to buy (ask), Sell = user gets selling
    # (bid). Sorted by Buy Price, high→low.
    names = [(r["source_en"] or r["source"])[:14] for r in lb]
    buys = [_num_en(r["user_buy_price"]) for r in lb]
    sells = [_num_en(r["user_sell_price"]) for r in lb]
    wn = max([len("Market")] + [len(x) for x in names]) if names else len("Market")
    wb = max([len("Buy Price")] + [len(x) for x in buys]) if buys else len("Buy Price")
    ws = max([len("Sell Price")] + [len(x) for x in sells]) if sells else len("Sell Price")

    def box(name: str, buy: str, sell: str) -> str:
        return f"| {name:<{wn}} | {buy:>{wb}} | {sell:>{ws}} |"

    sep = "|" + "-" * (wn + 2) + "|" + "-" * (wb + 2) + "|" + "-" * (ws + 2) + "|"
    # 3-cell left margin: "🔸 " (emoji≈2 + space) for Gerami, three spaces otherwise,
    # so the table box lines up across every row while Gerami stays marked.
    table = ["   " + box("Market", "Buy Price", "Sell Price"), "   " + sep]
    for r, name, buy, sell in zip(lb, names, buys, sells):
        mark = "🔸 " if r["is_gerami"] else "   "
        table.append(mark + box(name, buy, sell))

    return "\n".join(out) + "\n\n<pre>\n" + _esc("\n".join(table)) + "\n</pre>"

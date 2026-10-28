"""Gerador v2 da fonte sintética de marketing (tracking de primeira parte, tipo GA4/GTM).

Diferente do v1, modela jornadas: cada visitante (visitor_id, cookie anônimo) pode clicar em
várias campanhas antes de enviar um formulário, e o envio liga a jornada ao Lead pelo e-mail.
Não toca no Salesforce: Leads e as 8 campanhas originais vêm do backup do RAW (16/out/2026).
Ver PLANO.md seção 7 (26/out/2026) para o desenho.
"""
import csv
import gzip
import json
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)

BACKUP_DIR = Path.home() / "backups" / "crm-lakehouse-raw-20261016"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# --- Janela fixa (reprodutível, diferente das datas relativas do v1) ---
WINDOW_START = date(2025, 3, 1)
WINDOW_END = date(2026, 8, 31)
CAMPAIGN_WEEKS = (10, 24)

# --- Campanhas novas (as 8 originais vêm do backup) ---
NEW_CAMPAIGNS = [
    {"utm_source": "newsletter", "utm_medium": "email", "utm_campaign": "newsletter_mensal"},
    {"utm_source": "linkedin", "utm_medium": "paid_social", "utm_campaign": "abm_decisores"},
]

# --- Jornadas ---
N_LOST_PROPAGATION = 30       # Leads sem UTM no CRM que vieram de marketing (perda de rastreamento)
N_NON_CONVERTING = 6000       # visitantes que clicam e nunca enviam formulário (~1,5% visitante → Lead)
TOUCHES_WEIGHTS = {1: 0.35, 2: 0.25, 3: 0.20, 4: 0.12, 5: 0.05, 6: 0.03}
LOOKBACK_DAYS = 60            # cliques anteriores ao envio ficam dentro dessa janela
NON_CONVERTING_CLICKS = (1, 3)

# --- Sujeira proposital ---
RATE_EMAIL_DIRTY = 0.10       # e-mail digitado com caixa/espaço diferente do CRM
RATE_CROSS_DEVICE = 0.10      # primeiros cliques da jornada em outro dispositivo (outro visitor_id)
RATE_ORPHAN_SUBMISSIONS = 0.05  # envios sem Lead no CRM (spam, falha na integração)
RATE_POST_CONVERSION = 0.20   # visitantes que voltam a clicar depois de converter
PLATFORM_CLICK_FACTOR = (1.10, 1.25)  # plataforma conta mais cliques que o site rastreia

# --- Reengajamento: Lead que já converteu volta e envia outro formulário (demo depois do e-book) ---
REENGAGEMENT_SEED = 43         # gerador separado: não altera as jornadas de aquisição já geradas
RATE_REENGAGEMENT = 0.20       # fração dos Leads que enviam pelo menos mais um formulário
MAX_EXTRA_SUBMISSIONS = 2
REENGAGEMENT_GAP_DAYS = (15, 120)
REENGAGEMENT_TOUCHES_WEIGHTS = {0: 0.25, 1: 0.35, 2: 0.25, 3: 0.15}  # 0 = voltou direto, sem clique

# --- Newsletter: pressupõe a pessoa já na base, então nunca é o primeiro clique do visitante ---
NEWSLETTER_FIX_SEED = 45       # gerador separado: não altera o resto dos dados

# --- Custo/desempenho (faixas de B2B SaaS; as do v1 davam ROAS ~105x) ---
CTR_RANGE = (0.01, 0.03)
CPC_RANGES = {
    "google": (6.00, 15.00),
    "meta": (2.50, 7.00),
    "linkedin": (10.00, 22.00),
    "newsletter": (0.0, 0.0),
}


def new_id(rng: random.Random = random) -> str:
    """UUID que segue a seed (o uuid4() do v1 mudava a cada execução)."""
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def read_backup(table: str) -> list[dict]:
    with gzip.open(BACKUP_DIR / f"{table}.json.gz", "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_leads() -> list[dict]:
    leads = [
        {
            "lead_id": r["ID"],
            "email": r["EMAIL"],
            "utm_source": r["UTM_SOURCE__C"],
            "utm_medium": r["UTM_MEDIUM__C"],
            "utm_campaign": r["UTM_CAMPAIGN__C"],
        }
        for r in read_backup("lead")
        if not r["ISDELETED"]
    ]
    return sorted(leads, key=lambda l: l["lead_id"])


def load_existing_campaigns() -> list[dict]:
    campaigns = [
        {
            "campaign_id": r["CAMPAIGN_ID"],
            "utm_source": r["UTM_SOURCE"],
            "utm_medium": r["UTM_MEDIUM"],
            "utm_campaign": r["UTM_CAMPAIGN"],
        }
        for r in read_backup("marketing_campaigns")
    ]
    return sorted(campaigns, key=lambda c: c["campaign_id"])


def assign_campaign_windows(campaigns: list[dict]) -> None:
    window_days = (WINDOW_END - WINDOW_START).days
    for c in campaigns:
        duration = random.randint(*CAMPAIGN_WEEKS) * 7
        start = WINDOW_START + timedelta(days=random.randint(0, window_days - duration))
        c["start_date"] = start
        c["end_date"] = start + timedelta(days=duration)
        c["ctr"] = random.uniform(*CTR_RANGE)
        c["cpc"] = random.uniform(*CPC_RANGES[c["utm_source"]])


def active_campaigns(campaigns: list[dict], on: date) -> list[dict]:
    return [c for c in campaigns if c["start_date"] <= on <= c["end_date"]]


def random_moment_in(campaign: dict) -> datetime:
    """Instante aleatório dentro da janela da campanha."""
    span = (campaign["end_date"] - campaign["start_date"]).days * 86400 + 86399
    return datetime.combine(campaign["start_date"], datetime.min.time()) + timedelta(
        seconds=random.randint(0, span)
    )


def make_click(visitor_id: str, campaign: dict, at: datetime, rng: random.Random = random) -> dict:
    return {
        "click_id": new_id(rng),
        "visitor_id": visitor_id,
        "campaign_id": campaign["campaign_id"],
        "utm_source": campaign["utm_source"],
        "utm_medium": campaign["utm_medium"],
        "utm_campaign": campaign["utm_campaign"],
        "event_timestamp": at,
    }


def earlier_touches(visitor_id: str, campaigns: list[dict], before: datetime, n: int) -> list[dict]:
    """n cliques nos LOOKBACK_DAYS antes de `before`, cada um numa campanha ativa naquela data.
    Data sem campanha ativa é sorteada de novo; se não achar, o toque é descartado."""
    clicks = []
    for _ in range(n):
        for _attempt in range(20):
            at = before - timedelta(seconds=random.randint(3600, LOOKBACK_DAYS * 86400))
            options = active_campaigns(campaigns, at.date())
            if options:
                clicks.append(make_click(visitor_id, random.choice(options), at))
                break
    return clicks


def dirty_email(email: str, rng: random.Random = random) -> str:
    local, domain = email.split("@")
    return rng.choice([
        f"{local.capitalize()}@{domain}",
        email.upper(),
        f"{email} ",
        f" {email}",
    ])


def build_converting_journeys(leads: list[dict], campaigns: list[dict]) -> tuple[list[dict], list[dict]]:
    """Leads com UTM no CRM: último clique = campanha do UTM (last-touch capturado pelo campo
    oculto do formulário). Mais N_LOST_PROPAGATION Leads sem UTM que também vieram de marketing."""
    by_utm = {(c["utm_source"], c["utm_medium"], c["utm_campaign"]): c for c in campaigns}

    with_utm = [l for l in leads if l["utm_campaign"]]
    without_utm = [l for l in leads if not l["utm_campaign"]]
    lost = random.sample(without_utm, k=N_LOST_PROPAGATION)

    clicks, submissions = [], []
    for lead in with_utm + lost:
        if lead["utm_campaign"]:
            last_campaign = by_utm[(lead["utm_source"], lead["utm_medium"], lead["utm_campaign"])]
        else:
            last_campaign = random.choice(campaigns)

        visitor_id = new_id()
        submitted_at = random_moment_in(last_campaign)
        last_click_at = submitted_at - timedelta(minutes=random.randint(1, 30))
        n_touches = random.choices(list(TOUCHES_WEIGHTS), weights=TOUCHES_WEIGHTS.values())[0]

        journey = earlier_touches(visitor_id, campaigns, last_click_at, n_touches - 1)
        journey.append(make_click(visitor_id, last_campaign, last_click_at))

        # cross-device: os primeiros toques ficam num visitor_id que nunca envia formulário
        if len(journey) > 1 and random.random() < RATE_CROSS_DEVICE:
            other_device = new_id()
            journey.sort(key=lambda c: c["event_timestamp"])
            for click in journey[: random.randint(1, len(journey) - 1)]:
                click["visitor_id"] = other_device

        # o visitante volta depois de converter: não pode contar na atribuição
        if random.random() < RATE_POST_CONVERSION:
            for _ in range(random.randint(1, 2)):
                at = submitted_at + timedelta(seconds=random.randint(3600, 30 * 86400))
                options = active_campaigns(campaigns, at.date())
                if options:
                    journey.append(make_click(visitor_id, random.choice(options), at))

        email = dirty_email(lead["email"]) if random.random() < RATE_EMAIL_DIRTY else lead["email"]
        submissions.append({
            "submission_id": new_id(),
            "visitor_id": visitor_id,
            "email": email,
            "submitted_at": submitted_at,
            "lead_email": lead["email"],  # só para o reengajamento, não vai para o CSV
        })
        clicks.extend(journey)

    return clicks, submissions


def build_reengagement(submissions: list[dict], campaigns: list[dict]) -> tuple[list[dict], list[dict]]:
    """Novos envios de Leads que já converteram, cada um 15–120 dias depois do anterior, com 0–3
    toques entre os dois envios. Usa um gerador próprio para não mudar as jornadas de aquisição."""
    rng = random.Random(REENGAGEMENT_SEED)
    window_end = datetime.combine(WINDOW_END, datetime.max.time())

    clicks, new_submissions = [], []
    for first in submissions:
        if rng.random() >= RATE_REENGAGEMENT:
            continue
        previous_at = first["submitted_at"]
        for _ in range(rng.randint(1, MAX_EXTRA_SUBMISSIONS)):
            submitted_at = previous_at + timedelta(
                days=rng.randint(*REENGAGEMENT_GAP_DAYS), seconds=rng.randint(0, 86399)
            )
            if submitted_at > window_end:
                break
            gap_seconds = int((submitted_at - previous_at).total_seconds())
            n_touches = rng.choices(list(REENGAGEMENT_TOUCHES_WEIGHTS), weights=REENGAGEMENT_TOUCHES_WEIGHTS.values())[0]
            for _ in range(n_touches):
                at = previous_at + timedelta(seconds=rng.randint(3600, gap_seconds - 60))
                options = active_campaigns(campaigns, at.date())
                if options:
                    clicks.append(make_click(first["visitor_id"], rng.choice(options), at, rng))

            email = dirty_email(first["lead_email"], rng) if rng.random() < RATE_EMAIL_DIRTY else first["lead_email"]
            new_submissions.append({
                "submission_id": new_id(rng),
                "visitor_id": first["visitor_id"],
                "email": email,
                "submitted_at": submitted_at,
            })
            previous_at = submitted_at
    return clicks, new_submissions


def build_orphan_submissions(campaigns: list[dict], n_converting: int) -> tuple[list[dict], list[dict]]:
    """Envios cujo e-mail não existe no CRM — cada um com um clique na mesma sessão."""
    clicks, submissions = [], []
    for i in range(round(n_converting * RATE_ORPHAN_SUBMISSIONS)):
        visitor_id = new_id()
        campaign = random.choice(campaigns)
        submitted_at = random_moment_in(campaign)
        clicks.append(make_click(visitor_id, campaign, submitted_at - timedelta(minutes=random.randint(1, 30))))
        submissions.append({
            "submission_id": new_id(),
            "visitor_id": visitor_id,
            "email": f"contato{i + 1}@exemplo-sem-crm.com.br",
            "submitted_at": submitted_at,
        })
    return clicks, submissions


def build_non_converting_visitors(campaigns: list[dict]) -> list[dict]:
    clicks = []
    for _ in range(N_NON_CONVERTING):
        visitor_id = new_id()
        first_campaign = random.choice(campaigns)
        first_at = random_moment_in(first_campaign)
        clicks.append(make_click(visitor_id, first_campaign, first_at))
        for _ in range(random.randint(*NON_CONVERTING_CLICKS) - 1):
            at = first_at + timedelta(seconds=random.randint(3600, 30 * 86400))
            options = active_campaigns(campaigns, at.date())
            if options:
                clicks.append(make_click(visitor_id, random.choice(options), at))
    return clicks


def fix_newsletter_first_touch(clicks: list[dict], campaigns: list[dict]) -> int:
    """Troca a campanha do primeiro clique do visitante quando é a newsletter (só recebe quem já está
    na base) por outra ativa na mesma data. Usa um gerador próprio para não mudar o resto dos dados."""
    rng = random.Random(NEWSLETTER_FIX_SEED)
    first_click: dict[str, dict] = {}
    for click in clicks:
        if click["visitor_id"] not in first_click:
            first_click[click["visitor_id"]] = click
    fixed = 0
    for click in first_click.values():
        if click["utm_source"] != "newsletter":
            continue
        options = [c for c in active_campaigns(campaigns, click["event_timestamp"].date())
                   if c["utm_source"] != "newsletter"]
        if options:
            campaign = rng.choice(options)
            click.update({k: campaign[k] for k in ("campaign_id", "utm_source", "utm_medium", "utm_campaign")})
            fixed += 1
    return fixed


def build_daily_stats(campaigns: list[dict], clicks: list[dict]) -> list[dict]:
    """Grão campanha × dia, como uma API de plataforma de anúncio entregaria. A plataforma conta
    mais cliques que o site rastreia (ad blocker, bounce antes da tag disparar)."""
    tracked: dict[tuple[str, date], int] = {}
    for click in clicks:
        key = (click["campaign_id"], click["event_timestamp"].date())
        tracked[key] = tracked.get(key, 0) + 1

    stats = []
    for c in campaigns:
        day = c["start_date"]
        while day <= c["end_date"]:
            platform_clicks = round(tracked.get((c["campaign_id"], day), 0) * random.uniform(*PLATFORM_CLICK_FACTOR))
            ctr = c["ctr"] * random.uniform(0.8, 1.2)
            stats.append({
                "campaign_id": c["campaign_id"],
                "stat_date": day,
                "impressions": round(max(platform_clicks, 1) / ctr),
                "clicks": platform_clicks,
                "cost": round(platform_clicks * c["cpc"] * random.uniform(0.85, 1.15), 2),
            })
            day += timedelta(days=1)
    return stats


def write_csv(filename: str, rows: list[dict], fields: list[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Gravado: {path} ({len(rows)} linhas)")


def main():
    leads = load_leads()
    campaigns = load_existing_campaigns()
    print(f"{len(leads)} Leads ({sum(1 for l in leads if l['utm_campaign'])} com UTM), {len(campaigns)} campanhas originais.")

    for spec in NEW_CAMPAIGNS:
        campaigns.append({"campaign_id": new_id(), **spec})
    assign_campaign_windows(campaigns)

    journey_clicks, submissions = build_converting_journeys(leads, campaigns)
    orphan_clicks, orphan_submissions = build_orphan_submissions(campaigns, len(submissions))
    clicks = journey_clicks + orphan_clicks + build_non_converting_visitors(campaigns)
    reengagement_clicks, reengagement_submissions = build_reengagement(submissions, campaigns)
    clicks += reengagement_clicks
    submissions += orphan_submissions + reengagement_submissions
    clicks.sort(key=lambda c: c["event_timestamp"])
    print(f"Newsletter como primeiro clique trocada em {fix_newsletter_first_touch(clicks, campaigns)} visitantes.")
    submissions.sort(key=lambda s: s["submitted_at"])
    daily_stats = build_daily_stats(campaigns, clicks)

    write_csv("marketing_campaigns.csv", campaigns,
              ["campaign_id", "utm_source", "utm_medium", "utm_campaign", "start_date", "end_date"])
    write_csv("marketing_click_events.csv", clicks,
              ["click_id", "visitor_id", "campaign_id", "utm_source", "utm_medium", "utm_campaign", "event_timestamp"])
    write_csv("marketing_form_submissions.csv", submissions,
              ["submission_id", "visitor_id", "email", "submitted_at"])
    write_csv("marketing_campaign_daily_stats.csv", daily_stats,
              ["campaign_id", "stat_date", "impressions", "clicks", "cost"])
    print("Concluído.")


if __name__ == "__main__":
    main()
